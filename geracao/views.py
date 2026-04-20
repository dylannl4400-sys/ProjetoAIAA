"""
geracao/views.py

Responsabilidade: geração de peças processuais a partir de templates.
"""
import json
import os
import tempfile

from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from document_generator import DocumentGenerator, CasoDespedimento
from geracao.models import PecaGerada
from aiaa_init import get_store, get_llm, get_generator


@csrf_exempt
@require_POST
def gerar_peca(request):
    """
    POST /geracao/gerar/
    Body: JSON com campos do CasoDespedimento
    Returns: ficheiro .docx
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    caso = CasoDespedimento(
        nome_trabalhador         = body.get("nome_trabalhador", ""),
        nif_trabalhador          = body.get("nif_trabalhador", ""),
        morada_trabalhador       = body.get("morada_trabalhador", ""),
        categoria_profissional   = body.get("categoria_profissional", ""),
        data_admissao            = body.get("data_admissao", ""),
        numero_contrato          = body.get("numero_contrato", ""),
        nome_empregador          = body.get("nome_empregador", ""),
        nif_empregador           = body.get("nif_empregador", ""),
        morada_empregador        = body.get("morada_empregador", ""),
        representante_empregador = body.get("representante_empregador", ""),
        cargo_representante      = body.get("cargo_representante", ""),
        nome_escritorio          = body.get("nome_escritorio", ""),
        referencia_processo      = body.get("referencia_processo", ""),
        motivo_cessacao          = body.get("motivo_cessacao", "Justa Causa Disciplinar"),
        descricao_factos         = body.get("descricao_factos", ""),
        artigo_cessacao          = body.get("artigo_cessacao", "351.º e 357.º"),
        data_efeitos             = body.get("data_efeitos", ""),
        local_data               = body.get("local_data", ""),
    )

    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    tmp.close()

    try:
        caminho = get_generator().gerar(caso, output_path=tmp.name)

        # Registar na BD
        PecaGerada.objects.create(
            trabalhador=caso.nome_trabalhador,
            processo   =caso.referencia_processo,
        )

        nome_ficheiro = f"carta_cessacao_{caso.nome_trabalhador.replace(' ', '_') or 'documento'}.docx"
        return FileResponse(
            open(caminho, "rb"),
            as_attachment=True,
            filename=nome_ficheiro,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def templates_listar(request):
    """GET /geracao/templates/ — lista templates disponíveis."""
    from geracao.models import Template
    templates = Template.objects.filter(ativo=True)
    return JsonResponse({
        "templates": [{"id": t.id, "nome": t.nome, "descricao": t.descricao}
                      for t in templates]
    })