"""
document_generator.py

Geração de peças jurídicas a partir de templates.

Fluxo:
    dados do caso + template
        ↓
    DocumentGenerator
        ├── VectorStore.search(contexto factual)  → artigos relevantes
        ├── LLM.generate(prompt de preenchimento) → fundamentação gerada
        └── node gerar_peca.js (template escolhido) → ficheiro .docx

Templates disponíveis (em templates/):
    carta_cessacao   → Carta de Cessação de Contrato de Trabalho
    (mais templates a adicionar conforme necessidade da sociedade de advogados)

Uso básico:
    from document_generator import DocumentGenerator, CasoDespedimento
    from config import load_config, build_embedder, build_store, build_llm

    cfg      = load_config()
    store    = build_store(cfg.vector_store, build_embedder(cfg.embedder))
    llm      = build_llm(cfg.llm)
    gen      = DocumentGenerator(store, llm)

    caso = CasoDespedimento(
        nome_trabalhador     = "Maria Filomena Costa",
        nome_empregador      = "Tecniworks, S.A.",
        data_efeitos         = "31 de outubro de 2024",
        descricao_factos     = "Emissão de facturas falsas...",
        # ... restantes campos
    )
    caminho = gen.gerar(caso, output_path="carta_cessacao.docx")
    print(f"Documento gerado: {caminho}")
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Optional

# Path to the JS template generator — same directory as this file
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_JS_TEMPLATE = os.path.join(_SCRIPT_DIR, "gerar_peca.js")


# ---------------------------------------------------------------------------
# Data classes — one per template type
# ---------------------------------------------------------------------------

@dataclass
class CasoDespedimento:
    """
    Dados necessários para gerar uma Carta de Cessação de Contrato de Trabalho.
    Campos com default vazios são preenchidos pelo LLM se não fornecidos.
    """
    # Trabalhador
    nome_trabalhador:       str = ""
    nif_trabalhador:        str = ""
    morada_trabalhador:     str = ""
    categoria_profissional: str = ""
    data_admissao:          str = ""
    numero_contrato:        str = ""

    # Empregador
    nome_empregador:        str = ""
    nif_empregador:         str = ""
    morada_empregador:      str = ""
    representante_empregador: str = ""
    cargo_representante:    str = ""
    nome_escritorio:        str = ""
    referencia_processo:    str = ""

    # Cessação
    motivo_cessacao:        str = "Justa Causa Disciplinar"
    descricao_factos:       str = ""
    fundamentacao_factual:  str = ""
    artigo_cessacao:        str = "351.º e 357.º"
    data_efeitos:           str = ""
    local_data:             str = ""


# ---------------------------------------------------------------------------
# DocumentGenerator
# ---------------------------------------------------------------------------

class DocumentGenerator:
    """
    Orquestra a geração de peças jurídicas:
    1. Recupera artigos relevantes do ChromaDB com base nos factos do caso
    2. Usa o LLM para gerar/completar a fundamentação jurídica
    3. Chama o template JS para produzir o ficheiro .docx final
    """

    # Prompt de sistema para geração de fundamentação
    _SYSTEM_PROMPT = """És um assistente jurídico especializado em direito do trabalho português.
Com base nos factos fornecidos e nas fontes jurídicas recuperadas, gera uma fundamentação
jurídica formal e precisa em português europeu.
A fundamentação deve:
- Citar apenas artigos que existam nas fontes fornecidas
- Usar linguagem jurídica formal
- Ser concisa (máximo 3 parágrafos)
- Não inventar referências legais
Responde APENAS com o texto da fundamentação, sem preâmbulo."""

    def __init__(self, store, llm, n_results: int = 5):
        self._store      = store
        self._llm        = llm
        self._n_results  = n_results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def gerar(
        self,
        caso: CasoDespedimento,
        output_path: str = "peca_juridica.docx",
        enriquecer_com_llm: bool = True,
    ) -> str:
        """
        Gera o ficheiro .docx da peça jurídica.

        Args:
            caso:               Dados do caso (CasoDespedimento ou similar)
            output_path:        Caminho do ficheiro de saída
            enriquecer_com_llm: Se True, usa o LLM para completar a fundamentação

        Returns:
            Caminho absoluto do ficheiro gerado
        """
        data = asdict(caso)

        # 1. Recuperar artigos relevantes do ChromaDB
        if caso.descricao_factos:
            chunks = self._store.search(caso.descricao_factos, n=self._n_results)
        else:
            chunks = []

        # 2. Enriquecer fundamentação com LLM (opcional)
        if enriquecer_com_llm and chunks and not caso.fundamentacao_factual:
            data["fundamentacao_factual"] = self._gerar_fundamentacao(caso, chunks)

        # 3. Preencher local_data se não fornecido
        if not data.get("local_data"):
            from datetime import date
            hoje = date.today()
            meses = ["janeiro","fevereiro","março","abril","maio","junho",
                     "julho","agosto","setembro","outubro","novembro","dezembro"]
            data["local_data"] = f"Lisboa, {hoje.day} de {meses[hoje.month-1]} de {hoje.year}"

        # 4. Gerar .docx via Node.js
        return self._run_js_template(data, output_path)

    def gerar_preview(self, caso: CasoDespedimento) -> dict:
        """
        Devolve os dados que seriam enviados ao template, sem gerar o ficheiro.
        Útil para validar o conteúdo antes de gerar o .docx.
        """
        data   = asdict(caso)
        chunks = []
        if caso.descricao_factos:
            chunks = self._store.search(caso.descricao_factos, n=self._n_results)

        return {
            "dados":  data,
            "fontes": [
                {
                    "score":    round(c["score"], 2),
                    "seccao":   c["metadata"].get("section", ""),
                    "ficheiro": c["metadata"].get("filename", ""),
                    "preview":  c["text"][:120],
                }
                for c in chunks
            ]
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _gerar_fundamentacao(self, caso: CasoDespedimento, chunks: list) -> str:
        """Ask the LLM to generate legal reasoning based on retrieved chunks."""
        fontes = "\n\n".join([
            f"[{i+1}] {c['metadata'].get('section','')}\n{c['text']}"
            for i, c in enumerate(chunks)
        ])

        prompt = f"""{self._SYSTEM_PROMPT}

FACTOS DO CASO:
{caso.descricao_factos}

FONTES JURÍDICAS DISPONÍVEIS:
{fontes}

FUNDAMENTAÇÃO:"""

        try:
            return self._llm.generate(prompt)
        except Exception as e:
            return f"[Fundamentação não gerada automaticamente: {e}]"

    def _run_js_template(self, data: dict, output_path: str) -> str:
        """Call the Node.js template script to produce the .docx file."""
        if not os.path.exists(_JS_TEMPLATE):
            raise FileNotFoundError(
                f"Template JS não encontrado: {_JS_TEMPLATE}\n"
                "Certifica-te que o ficheiro gerar_peca.js está na mesma pasta."
            )

        output_path = os.path.abspath(output_path)
        data_json   = json.dumps(data, ensure_ascii=False)

        result = subprocess.run(
            ["node", _JS_TEMPLATE, data_json, output_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Erro ao gerar documento:\n{result.stderr}\n{result.stdout}"
            )

        return output_path
