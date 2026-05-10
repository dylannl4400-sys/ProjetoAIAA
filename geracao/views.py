# """
# geracao/views.py
# """
# import json, os, tempfile
# from django.http import JsonResponse, FileResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_POST
# from aiaa_init import get_llm


# @csrf_exempt
# @require_POST
# def gerar_peca(request):
#     """
#     POST /geracao/gerar/
#     Body: { template, nome_parte_a, nome_parte_b, descricao_factos, pedido, ... }
#     Returns: ficheiro .docx
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     tipo = body.get("template", "contestacao")

#     # Campos obrigatórios
#     if not body.get("nome_parte_a") or not body.get("descricao_factos"):
#         return JsonResponse({"erro": "Campos obrigatórios em falta."}, status=400)

#     try:
#         from template_generator import gerar_peca_processual
#         caminho = gerar_peca_processual(tipo=tipo, dados=body, llm=get_llm())

#         # Guardar registo
#         try:
#             from geracao.models import PecaGerada
#             PecaGerada.objects.create(
#                 trabalhador=body.get("nome_parte_a", ""),
#                 processo   =body.get("referencia_processo", ""),
#             )
#         except Exception:
#             pass

#         nome_ficheiro = f"{tipo}_{body.get('nome_parte_a','').replace(' ','_')}.docx"
#         return FileResponse(
#             open(caminho, "rb"),
#             as_attachment=True,
#             filename=nome_ficheiro,
#             content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#         )
#     except FileNotFoundError as e:
#         return JsonResponse({"erro": f"Template não encontrado: {e}"}, status=404)
#     except ImportError as e:
#         return JsonResponse({"erro": f"Dependência em falta: pip install python-docx ({e})"}, status=500)
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         return JsonResponse({"erro": str(e)}, status=500)


# def templates_listar(request):
#     """GET /geracao/templates/"""
#     templates = [
#         {"id": "contestacao",  "nome": "Contestação",                    "descricao": "Resposta do réu à petição inicial"},
#         {"id": "peticao",      "nome": "Petição Inicial",                "descricao": "Acção de intimação para protecção de direitos"},
#         {"id": "requerimento", "nome": "Requerimento",                   "descricao": "Incidente processual ou pedido ao tribunal"},
#         {"id": "cessacao",     "nome": "Carta de Cessação de Contrato",  "descricao": "Comunicação de despedimento ao trabalhador"},
#     ]
#     return JsonResponse({"templates": templates})

"""
geracao/views.py

Dois modos de geração:
    POST /geracao/gerar/         → modo simples (sem RAG)
    POST /geracao/gerar-rag/     → modo RAG (com acórdãos indexados)
"""
import json, os, tempfile
from django.http  import JsonResponse, FileResponse
from django.views.decorators.csrf  import csrf_exempt
from django.views.decorators.http  import require_POST
from aiaa_init import get_llm, get_store


TIPOS_VALIDOS = {"contestacao", "peticao", "requerimento"}


def _validar(body: dict) -> str | None:
    """Devolve mensagem de erro ou None se OK."""
    from geracao.models import Template
    if not Template.objects.filter(identificador=body.get("template"), ativo=True).exists():
        return f"Template '{body.get('template')}' não encontrado ou inactivo."
    if not body.get("nome_parte_a", "").strip():
        return "nome_parte_a obrigatório."
    if not body.get("descricao_factos", "").strip():
        return "descricao_factos obrigatório."
    return None


def _gerar_e_devolver(body: dict, usar_rag: bool):
    """Lógica comum a ambas as views."""
    erro = _validar(body)
    if erro:
        return JsonResponse({"erro": erro}, status=400)

    tipo = body["template"]

    try:
        from template_generator import TemplateGenerator

        from geracao.models import Template
        template_obj = Template.objects.get(identificador=tipo)

        # Se usar_rag é False, não passamos LLM para fazer apenas substituição direta
        gen = TemplateGenerator(
            llm   = get_llm() if usar_rag else None,
            store = get_store() if usar_rag else None,
        )

        conteudo = gen._gerar_conteudo(tipo, body)
        # Passar o conteúdo já gerado para o método gerar para evitar a segunda chamada (se o método suportar)
        # Caso o método não suporte, removemos a chamada interna no gerar() se necessário.
        caminho  = gen.gerar(template_obj.nome_ficheiro_docx, body, conteudo=conteudo)

        # Guardar registo na BD
        try:
            from geracao.models import PecaGerada
            PecaGerada.objects.create(
                trabalhador = body.get("nome_parte_a", ""),
                processo    = body.get("referencia_processo", ""),
            )
        except Exception:
            pass

        # Headers extra para info sobre RAG
        acordaos_usados = conteudo.get("acordaos", [])
        nome_ficheiro   = f"{tipo}_{body.get('nome_parte_a','').replace(' ','_')}.docx"

        resp = FileResponse(
            open(caminho, "rb"),
            as_attachment=True,
            filename=nome_ficheiro,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        # Indicar no header quantos acórdãos foram usados
        resp["X-Acordaos-RAG"] = str(len(acordaos_usados))
        resp["X-Fonte"]        = conteudo.get("fonte", "?")
        return resp

    except FileNotFoundError as e:
        return JsonResponse({"erro": f"Template não encontrado: {e}"}, status=404)
    except ImportError as e:
        return JsonResponse({"erro": f"pip install python-docx ({e})"}, status=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"erro": str(e)}, status=500)


@csrf_exempt
@require_POST
def gerar_peca(request):
    """
    POST /geracao/gerar/
    Modo simples — LLM usa apenas os dados do formulário.
    Não requer acórdãos indexados.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)
    return _gerar_e_devolver(body, usar_rag=False)


@csrf_exempt
@require_POST
def gerar_peca_rag(request):
    """
    POST /geracao/gerar-rag/
    Modo RAG — LLM usa dados + acórdãos indexados no ChromaDB.
    Produz fundamentação com jurisprudência real.
    Requer acórdãos do ITIJ indexados previamente.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)
    return _gerar_e_devolver(body, usar_rag=True)


def templates_listar(request):
    """GET /geracao/templates/"""
    from geracao.models import Template
    templates = Template.objects.filter(ativo=True)
    return JsonResponse({"templates": [
        {
            "id": t.identificador, 
            "nome": t.nome_exibicao, 
            "descricao": t.descricao
        } 
        for t in templates
    ]})