# """
# llm_chunker.py

# Chunker semântico para acórdãos jurídicos portugueses.

# Abordagem (sugerida pelo Prof. Paulo Trigo):
#     1. Dividir texto limpo em blocos fixos numerados (~2200 chars)
#     2. LLM classifica cada bloco numa secção semântica
#     3. Reconstruir secções concatenando blocos da mesma classe
#     4. Fallback para chunking fixo se LLM falhar

# Secções possíveis:
#     metadados, sumario, relatorio, factos,
#     fundamentacao_direito, decisao, outro

# Dependências:
#     pip install ollama requests
# """

# import json
# import re
# import requests
# from typing import Optional


# # Secções válidas
# SECCOES_VALIDAS = {
#     "metadados", "sumario", "relatorio", "factos",
#     "fundamentacao_direito", "decisao", "outro",
# }

# # Prompt de classificação (Prof. Paulo Trigo)
# _PROMPT_TEMPLATE = """Tarefa: Classificar semanticamente blocos consecutivos de um acórdão jurídico português.

# Objetivo:
# Para cada bloco, indicar a secção do acórdão a que pertence.

# Classes permitidas:
# - metadados
# - sumario
# - relatorio
# - factos
# - fundamentacao_direito
# - decisao
# - outro

# Definições:
# - metadados: tribunal, processo, relator, data, descritores
# - sumario: síntese inicial, muitas vezes numerada (I, II, III)
# - relatorio: descrição do caso, partes e tramitação processual
# - factos: factos provados/não provados, se explicitamente separados
# - fundamentacao_direito: análise jurídica e argumentação (normalmente a maior secção)
# - decisao: parte final dispositiva (ex: "decidem", "julga-se", "acorda-se")
# - outro: conteúdo residual que não encaixe claramente

# Regras:
# 1. Usa apenas uma classe por bloco.
# 2. Não resumir o conteúdo.
# 3. Não copiar texto dos blocos.
# 4. Não inventar classes novas.
# 5. Baseia-te no conteúdo semântico, não apenas em maiúsculas ou formatação.
# 6. Se houver dúvida entre "factos" e "fundamentacao_direito":
#    - "factos" apenas quando houver enumeração clara de factos provados/não provados
#    - caso contrário, usa "fundamentacao_direito"
# 7. "decisao" deve ser usada apenas para a parte final dispositiva.
# 8. Responde APENAS em JSON válido, sem texto adicional.

# Formato de saída:
# {{
#   "classificacao": [
#     {{"bloco": 1, "secao": "metadados"}},
#     {{"bloco": 2, "secao": "sumario"}},
#     {{"bloco": 3, "secao": "relatorio"}}
#   ]
# }}

# Blocos:
# {blocos}"""


# class LLMChunker:
#     """
#     Chunker semântico usando LLM para classificar blocos de texto.

#     Args:
#         base_url:   URL base do Ollama (ex: http://localhost:11434)
#         model:      nome do modelo Ollama
#         block_size: tamanho de cada bloco em caracteres
#         overlap:    sobreposição entre blocos
#         temperature: temperatura do LLM (0 = determinístico)
#         timeout:    timeout HTTP em segundos
#     """

#     def __init__(
#         self,
#         base_url:    str   = "http://localhost:11434",
#         model:       str   = "qwen2.5:7b-instruct-q4_K_M",
#         block_size:  int   = 2200,
#         overlap:     int   = 100,
#         temperature: float = 0.0,
#         timeout:     int   = 120,
#     ):
#         self.base_url    = base_url.rstrip("/")
#         self.model       = model
#         self.block_size  = block_size
#         self.overlap     = overlap
#         self.temperature = temperature
#         self.timeout     = timeout

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def classificar(self, texto: str) -> dict:
#         """
#         Classifica o texto em secções semânticas.

#         Returns:
#             {
#                 "status":   "ok" | "fallback",
#                 "reason":   str (só em fallback),
#                 "sections": {
#                     "metadados":            str,
#                     "sumario":              str,
#                     "relatorio":            str,
#                     "factos":               str,
#                     "fundamentacao_direito": str,
#                     "decisao":              str,
#                     "outro":                str,
#                 },
#                 "num_blocks": int,
#             }
#         """
#         blocos = self._dividir_em_blocos(texto)

#         try:
#             parsed   = self._classificar_com_llm(blocos)
#             valido   = self._validar(parsed, len(blocos))
#             if not valido:
#                 raise ValueError("Classificação inválida ou incompleta.")
#             sections = self._reconstruir_seccoes(blocos, parsed)
#             return {
#                 "status":       "ok",
#                 "num_blocks":   len(blocos),
#                 "classificacao": parsed["classificacao"],
#                 "sections":     sections,
#             }
#         except Exception as e:
#             # Fallback — chunking fixo rotulado como "outro"
#             return {
#                 "status":     "fallback",
#                 "reason":     str(e),
#                 "num_blocks": len(blocos),
#                 "sections": {
#                     s: "" for s in SECCOES_VALIDAS
#                 } | {"outro": texto},
#             }

#     def chunks_para_indexar(
#         self,
#         texto:     str,
#         metadados: str = "",
#         sumario:   str = "",
#     ) -> list[dict]:
#         """
#         Pipeline completo: classifica e devolve lista de chunks
#         prontos para indexar no ChromaDB.

#         Metadados e sumário são passados directamente (extraídos
#         deterministicamente pelo html_cleaner) e não entram na
#         classificação LLM.

#         Returns:
#             Lista de dicts com "text" e "section".
#         """
#         chunks = []

#         # Chunk de metadados (determinístico)
#         if metadados and metadados.strip():
#             chunks.append({"text": metadados.strip(), "section": "metadados", "chunk_idx": 0})

#         # Chunks de sumário (determinístico, subdividido se necessário)
#         if sumario and sumario.strip():
#             partes = self._subdividir(sumario.strip(), "sumario")
#             chunks.extend(partes)

#         # Corpo — classificação LLM
#         if texto and texto.strip():
#             resultado = self.classificar(texto.strip())
#             sections  = resultado.get("sections", {})

#             for seccao in ["relatorio", "factos", "fundamentacao_direito", "decisao", "outro"]:
#                 conteudo = sections.get(seccao, "").strip()
#                 if conteudo:
#                     partes = self._subdividir(conteudo, seccao)
#                     chunks.extend(partes)

#         return chunks

#     # ------------------------------------------------------------------
#     # Divisão em blocos
#     # ------------------------------------------------------------------

#     def _dividir_em_blocos(self, texto: str) -> list[str]:
#         """Divide texto em blocos com overlap, cortando em newline."""
#         blocos = []
#         start  = 0
#         n      = len(texto)

#         while start < n:
#             end = min(start + self.block_size, n)

#             # Cortar numa quebra de linha próxima do fim
#             if end < n:
#                 nl = texto.rfind("\n", start, end)
#                 if nl != -1 and nl > start + int(self.block_size * 0.6):
#                     end = nl

#             bloco = texto[start:end].strip()
#             if bloco:
#                 blocos.append(bloco)

#             if end >= n:
#                 break

#             start = max(end - self.overlap, start + 1)

#         return blocos

#     def _subdividir(self, texto: str, seccao: str) -> list[dict]:
#         """Subdivide uma secção longa em chunks de block_size."""
#         if len(texto) <= self.block_size:
#             return [{"text": texto, "section": seccao, "chunk_idx": 0}]
#         partes = self._dividir_em_blocos(texto)
#         return [{"text": p, "section": seccao, "chunk_idx": i} for i, p in enumerate(partes)]

#     # ------------------------------------------------------------------
#     # LLM
#     # ------------------------------------------------------------------

#     def _classificar_com_llm(self, blocos: list[str]) -> dict:
#         """Envia blocos ao LLM e devolve a classificação."""
#         blocos_fmt = "\n\n".join(
#             f"[BLOCO {i+1}]\n{b}" for i, b in enumerate(blocos)
#         )
#         prompt = _PROMPT_TEMPLATE.format(blocos=blocos_fmt)

#         resp = requests.post(
#             f"{self.base_url}/api/generate",
#             json={
#                 "model":  self.model,
#                 "prompt": prompt,
#                 "stream": False,
#                 "options": {"temperature": self.temperature},
#             },
#             headers={
#                 "ngrok-skip-browser-warning": "true",
#                 "User-Agent": "AIAA-Legal-Assistant",
#             },
#             timeout=self.timeout,
#         )
#         resp.raise_for_status()
#         raw = resp.json().get("response", "")
#         return self._extrair_json(raw)

#     def _extrair_json(self, texto: str) -> dict:
#         """Extrai JSON mesmo com ruído extra na resposta."""
#         texto = texto.strip()
#         try:
#             return json.loads(texto)
#         except json.JSONDecodeError:
#             pass
#         m = re.search(r"\{.*\}", texto, re.DOTALL)
#         if m:
#             try:
#                 return json.loads(m.group(0))
#             except json.JSONDecodeError:
#                 pass
#         raise ValueError(f"JSON inválido na resposta do LLM: {texto[:200]}")

#     # ------------------------------------------------------------------
#     # Validação e reconstrução
#     # ------------------------------------------------------------------

#     def _validar(self, parsed: dict, num_blocos: int) -> bool:
#         if "classificacao" not in parsed:
#             return False
#         if not isinstance(parsed["classificacao"], list):
#             return False
#         vistos = set()
#         for item in parsed["classificacao"]:
#             b = item.get("bloco")
#             s = item.get("secao")
#             if not isinstance(b, int) or b < 1 or b > num_blocos:
#                 return False
#             if s not in SECCOES_VALIDAS:
#                 return False
#             vistos.add(b)
#         return len(vistos) == num_blocos

#     def _reconstruir_seccoes(self, blocos: list[str], parsed: dict) -> dict:
#         """Agrupa blocos por secção e concatena."""
#         mapa: dict[str, list[str]] = {s: [] for s in SECCOES_VALIDAS}
#         for item in sorted(parsed["classificacao"], key=lambda x: x["bloco"]):
#             idx   = item["bloco"] - 1
#             secao = item["secao"]
#             mapa[secao].append(blocos[idx])
#         return {s: "\n\n".join(v).strip() for s, v in mapa.items()}
    
"""
llm_chunker.py

Chunker semântico para acórdãos jurídicos portugueses.

Abordagem (sugerida pelo Prof. Paulo Trigo):
    1. Dividir texto limpo em blocos fixos numerados (~2200 chars)
    2. LLM classifica cada bloco numa secção semântica
    3. Reconstruir secções concatenando blocos da mesma classe
    4. Fallback para chunking fixo se LLM falhar

Secções possíveis:
    metadados, sumario, relatorio, factos,
    fundamentacao_direito, decisao, outro

Dependências:
    pip install ollama requests
"""

import json
import re
import requests
from typing import Optional


# Secções válidas
SECCOES_VALIDAS = {
    "metadados", "sumario", "relatorio", "factos",
    "fundamentacao_direito", "decisao", "outro",
}

# Prompt de classificação (Prof. Paulo Trigo)
_PROMPT_TEMPLATE = """Tarefa: Classificar semanticamente blocos consecutivos de um acórdão jurídico português.

Objetivo:
Para cada bloco, indicar a secção do acórdão a que pertence.

Classes permitidas:
- metadados
- sumario
- relatorio
- factos
- fundamentacao_direito
- decisao
- outro

Definições:
- metadados: tribunal, processo, relator, data, descritores
- sumario: síntese inicial, muitas vezes numerada (I, II, III)
- relatorio: descrição do caso, partes e tramitação processual
- factos: factos provados/não provados, se explicitamente separados
- fundamentacao_direito: análise jurídica e argumentação (normalmente a maior secção)
- decisao: parte final dispositiva (ex: "decidem", "julga-se", "acorda-se")
- outro: conteúdo residual que não encaixe claramente

Regras:
1. Usa apenas uma classe por bloco.
2. Não resumir o conteúdo.
3. Não copiar texto dos blocos.
4. Não inventar classes novas.
5. Baseia-te no conteúdo semântico, não apenas em maiúsculas ou formatação.
6. Se houver dúvida entre "factos" e "fundamentacao_direito":
   - "factos" apenas quando houver enumeração clara de factos provados/não provados
   - caso contrário, usa "fundamentacao_direito"
7. "decisao" deve ser usada apenas para a parte final dispositiva.
8. Responde APENAS em JSON válido, sem texto adicional.

Formato de saída:
{{
  "classificacao": [
    {{"bloco": 1, "secao": "metadados"}},
    {{"bloco": 2, "secao": "sumario"}},
    {{"bloco": 3, "secao": "relatorio"}}
  ]
}}

Blocos:
{blocos}"""


class LLMChunker:
    """
    Chunker semântico usando LLM para classificar blocos de texto.

    Args:
        base_url:   URL base do Ollama (ex: http://localhost:11434)
        model:      nome do modelo Ollama
        block_size: tamanho de cada bloco em caracteres
        overlap:    sobreposição entre blocos
        temperature: temperatura do LLM (0 = determinístico)
        timeout:    timeout HTTP em segundos
    """

    def __init__(
        self,
        base_url:    str   = "http://localhost:11434",
        model:       str   = "qwen2.5:7b-instruct-q4_K_M",
        block_size:  int   = 2200,
        overlap:     int   = 100,
        temperature: float = 0.0,
        timeout:     int   = 120,
    ):
        self.base_url    = base_url.rstrip("/")
        self.model       = model
        self.block_size  = block_size
        self.overlap     = overlap
        self.temperature = temperature
        self.timeout     = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # Numero maximo de blocos por chamada ao LLM
    # Com block_size=2200 e ~400 chars/token, cada bloco tem ~5-6 tokens de texto
    # mais o prompt base (~500 tokens) => maximo seguro de 5 blocos por chamada
    MAX_BLOCOS_POR_LOTE = 5

    def classificar(self, texto: str) -> dict:
        """
        Classifica o texto em secções semânticas.
        Processa os blocos em lotes para evitar truncagem do contexto do LLM.

        Returns:
            {
                "status":   "ok" | "fallback",
                "reason":   str (so em fallback),
                "sections": {secção: texto, ...},
                "num_blocks": int,
            }
        """
        blocos = self._dividir_em_blocos(texto)

        try:
            classificacao = self._classificar_em_lotes(blocos)
            # Preencher blocos em falta com "outro"
            classificacao = self._preencher_em_falta(classificacao, len(blocos))
            parsed   = {"classificacao": classificacao}
            valido   = self._validar(parsed, len(blocos))
            if not valido:
                raise ValueError(f"Classificacao invalida: {len(classificacao)}/{len(blocos)} blocos.")
            sections = self._reconstruir_seccoes(blocos, parsed)
            return {
                "status":        "ok",
                "num_blocks":    len(blocos),
                "classificacao": classificacao,
                "sections":      sections,
            }
        except Exception as e:
            # Fallback — chunking fixo rotulado como "outro"
            return {
                "status":     "fallback",
                "reason":     str(e),
                "num_blocks": len(blocos),
                "sections":   {s: "" for s in SECCOES_VALIDAS} | {"outro": texto},
            }

    def _classificar_em_lotes(self, blocos: list[str]) -> list[dict]:
        """
        Classifica blocos em lotes de MAX_BLOCOS_POR_LOTE para
        nunca exceder o contexto do LLM.
        Mantém o offset do numero de bloco para reconstrucao correcta.
        """
        classificacao = []
        n = len(blocos)

        for inicio in range(0, n, self.MAX_BLOCOS_POR_LOTE):
            lote        = blocos[inicio: inicio + self.MAX_BLOCOS_POR_LOTE]
            offset      = inicio  # numero do primeiro bloco neste lote (0-based)

            parsed_lote = self._classificar_com_llm(lote, offset=offset)

            if "classificacao" not in parsed_lote:
                raise ValueError(f"Lote {inicio}-{inicio+len(lote)} nao devolveu classificacao.")

            classificacao.extend(parsed_lote["classificacao"])

        return classificacao

    def chunks_para_indexar(
        self,
        texto:     str,
        metadados: str = "",
        sumario:   str = "",
    ) -> list[dict]:
        """
        Pipeline completo: classifica e devolve lista de chunks
        prontos para indexar no ChromaDB.

        Metadados e sumário são passados directamente (extraídos
        deterministicamente pelo html_cleaner) e não entram na
        classificação LLM.

        Returns:
            Lista de dicts com "text" e "section".
        """
        chunks = []

        # Chunk de metadados (determinístico)
        if metadados and metadados.strip():
            chunks.append({"text": metadados.strip(), "section": "metadados", "chunk_idx": 0})

        # Chunks de sumário (determinístico, subdividido se necessário)
        if sumario and sumario.strip():
            partes = self._subdividir(sumario.strip(), "sumario")
            chunks.extend(partes)

        # Corpo — classificação LLM
        if texto and texto.strip():
            resultado = self.classificar(texto.strip())
            sections  = resultado.get("sections", {})

            for seccao in ["relatorio", "factos", "fundamentacao_direito", "decisao", "outro"]:
                conteudo = sections.get(seccao, "").strip()
                if conteudo:
                    partes = self._subdividir(conteudo, seccao)
                    chunks.extend(partes)

        return chunks

    # ------------------------------------------------------------------
    # Divisão em blocos
    # ------------------------------------------------------------------

    def _dividir_em_blocos(self, texto: str) -> list[str]:
        """Divide texto em blocos com overlap, cortando em newline."""
        blocos = []
        start  = 0
        n      = len(texto)

        while start < n:
            end = min(start + self.block_size, n)

            # Cortar numa quebra de linha próxima do fim
            if end < n:
                nl = texto.rfind("\n", start, end)
                if nl != -1 and nl > start + int(self.block_size * 0.6):
                    end = nl

            bloco = texto[start:end].strip()
            if bloco:
                blocos.append(bloco)

            if end >= n:
                break

            start = max(end - self.overlap, start + 1)

        return blocos

    def _subdividir(self, texto: str, seccao: str) -> list[dict]:
        """Subdivide uma secção longa em chunks de block_size."""
        if len(texto) <= self.block_size:
            return [{"text": texto, "section": seccao, "chunk_idx": 0}]
        partes = self._dividir_em_blocos(texto)
        return [{"text": p, "section": seccao, "chunk_idx": i} for i, p in enumerate(partes)]

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _classificar_com_llm(self, blocos: list[str], offset: int = 0) -> dict:
        """
        Envia um lote de blocos ao LLM e devolve a classificacao.
        offset: numero do primeiro bloco no lote (0-based) para manter
                numeracao global correcta na resposta.
        """
        blocos_fmt = "\n\n".join(
            f"[BLOCO {offset + i + 1}]\n{b}" for i, b in enumerate(blocos)
        )
        prompt = _PROMPT_TEMPLATE.format(blocos=blocos_fmt)

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model":  self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature},
            },
            headers={
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "AIAA-Legal-Assistant",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        return self._extrair_json(raw)

    def _extrair_json(self, texto: str) -> dict:
        """Extrai JSON mesmo com ruído extra na resposta."""
        texto = texto.strip()
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", texto, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"JSON inválido na resposta do LLM: {texto[:200]}")

    # ------------------------------------------------------------------
    # Validação e reconstrução
    # ------------------------------------------------------------------

    def _preencher_em_falta(self, classificacao: list, num_blocos: int) -> list:
        """Blocos nao classificados pelo LLM ficam como outro."""
        vistos = {item["bloco"] for item in classificacao if isinstance(item.get("bloco"), int)}
        for i in range(1, num_blocos + 1):
            if i not in vistos:
                classificacao.append({"bloco": i, "secao": "outro"})
        return sorted(classificacao, key=lambda x: x["bloco"])


    def _validar(self, parsed: dict, num_blocos: int) -> bool:
        if "classificacao" not in parsed:
            return False
        if not isinstance(parsed["classificacao"], list):
            return False
        vistos = set()
        for item in parsed["classificacao"]:
            b = item.get("bloco")
            s = item.get("secao")
            if not isinstance(b, int) or b < 1 or b > num_blocos:
                return False
            if s not in SECCOES_VALIDAS:
                return False
            vistos.add(b)
        return len(vistos) >= int(num_blocos * 0.8)  # tolerante: 80% classificados

    def _reconstruir_seccoes(self, blocos: list[str], parsed: dict) -> dict:
        """Agrupa blocos por secção e concatena."""
        mapa: dict[str, list[str]] = {s: [] for s in SECCOES_VALIDAS}
        for item in sorted(parsed["classificacao"], key=lambda x: x["bloco"]):
            idx   = item["bloco"] - 1
            secao = item["secao"]
            mapa[secao].append(blocos[idx])
        return {s: "\n\n".join(v).strip() for s, v in mapa.items()}