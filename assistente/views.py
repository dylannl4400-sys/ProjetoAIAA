# """
# assistente/views.py

# Django views for the AIAA RAG pipeline.

# The Retriever and all its components are initialised once when the
# Django process starts — not on every request. This keeps the embedding
# model in memory and avoids the multi-second startup cost per query.
# """

# import json
# import os
# import tempfile

# from django.http import JsonResponse, FileResponse
# from django.shortcuts import render
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_POST

# from config import load_config, build_embedder, build_store, \
#                    build_prompt_builder, build_llm, build_chunker
# from retriever import Retriever
# from document_generator import DocumentGenerator, CasoDespedimento
# from document_registry import registar_e_indexar, registar_e_indexar_itij

# # ---------------------------------------------------------------------------
# # One-time initialisation — runs when Django starts
# # ---------------------------------------------------------------------------

# _cfg       = load_config()
# _embedder  = build_embedder(_cfg.embedder)
# _store     = build_store(_cfg.vector_store, _embedder)
# _builder   = build_prompt_builder(_cfg.prompt_builder)
# _llm       = build_llm(_cfg.llm)
# _chunker   = build_chunker(_cfg.chunker)
# _retriever = Retriever(_store, _builder, _llm, _cfg.retriever.n_results)
# _generator = DocumentGenerator(_store, _llm)


# # ---------------------------------------------------------------------------
# # Views
# # ---------------------------------------------------------------------------

# def index(request):
#     """Serve the main chat interface."""
#     context = {
#         "modelo":   _cfg.llm.model_name,
#         "embedder": _cfg.embedder.model_name,
#         "n_docs":   _store.count(),
#     }
#     return render(request, "assistente/index.html", context)


# @csrf_exempt
# @require_POST
# def pergunta(request):
#     """
#     POST /api/pergunta/
#     Body: {"pergunta": "..."}
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     q = body.get("pergunta", "").strip()
#     if not q:
#         return JsonResponse({"erro": "Pergunta vazia."}, status=400)

#     if _store.count() == 0:
#         return JsonResponse(
#             {"erro": "Nenhum documento indexado. Corre primeiro: python indexar.py"},
#             status=503,
#         )

#     result = _retriever.ask(q)

#     # Construir mapa hash -> sumario para fontes que nao trazem sumario nos metadados
#     # (acórdaos indexados antes do novo pipeline nao tinham sumario nos metadados)
#     sumarios_cache = {}
#     for s in result.sources:
#         h = s["metadata"].get("hash_documento", "")
#         if h and not s["metadata"].get("sumario", ""):
#             if h not in sumarios_cache:
#                 try:
#                     chunks_sum = _store.search(
#                         "sumario acórdão",
#                         filters={"hash_documento": h, "section": "sumario"},
#                         n=1,
#                     )
#                     sumarios_cache[h] = chunks_sum[0]["text"][:500] if chunks_sum else ""
#                 except Exception:
#                     sumarios_cache[h] = ""

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("nome_ficheiro") or s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
#                 "processo": s["metadata"].get("processo", ""),
#                 "relator":  s["metadata"].get("relator", ""),
#                 "tribunal": s["metadata"].get("court", ""),
#                 "sumario":  s["metadata"].get("sumario", "") or sumarios_cache.get(s["metadata"].get("hash_documento", ""), ""),
#                 "url":      s["metadata"].get("url", ""),
#             }
#             for s in result.sources
#         ],
#     })


# @csrf_exempt
# @require_POST
# def gerar_peca(request):
#     """
#     POST /api/gerar_peca/
#     Body: JSON com os campos do CasoDespedimento
#     Returns: ficheiro .docx para download
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     caso = CasoDespedimento(
#         nome_trabalhador         = body.get("nome_trabalhador", ""),
#         nif_trabalhador          = body.get("nif_trabalhador", ""),
#         morada_trabalhador       = body.get("morada_trabalhador", ""),
#         categoria_profissional   = body.get("categoria_profissional", ""),
#         data_admissao            = body.get("data_admissao", ""),
#         numero_contrato          = body.get("numero_contrato", ""),
#         nome_empregador          = body.get("nome_empregador", ""),
#         nif_empregador           = body.get("nif_empregador", ""),
#         morada_empregador        = body.get("morada_empregador", ""),
#         representante_empregador = body.get("representante_empregador", ""),
#         cargo_representante      = body.get("cargo_representante", ""),
#         nome_escritorio          = body.get("nome_escritorio", ""),
#         referencia_processo      = body.get("referencia_processo", ""),
#         motivo_cessacao          = body.get("motivo_cessacao", "Justa Causa Disciplinar"),
#         descricao_factos         = body.get("descricao_factos", ""),
#         artigo_cessacao          = body.get("artigo_cessacao", "351.º e 357.º"),
#         data_efeitos             = body.get("data_efeitos", ""),
#         local_data               = body.get("local_data", ""),
#     )

#     tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
#     tmp.close()

#     try:
#         caminho       = _generator.gerar(caso, output_path=tmp.name)
#         nome_ficheiro = f"carta_cessacao_{caso.nome_trabalhador.replace(' ', '_') or 'documento'}.docx"
#         return FileResponse(
#             open(caminho, "rb"),
#             as_attachment=True,
#             filename=nome_ficheiro,
#             content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#         )
#     except Exception as e:
#         return JsonResponse({"erro": str(e)}, status=500)
#     finally:
#         try:
#             os.unlink(tmp.name)
#         except Exception:
#             pass


# @csrf_exempt
# def upload_documento(request):
#     """
#     POST /api/upload/
#     multipart/form-data:
#         ficheiro : PDF a indexar
#         type     : "ruling" | "legislation" | "document"
#         year     : ano (ex: "2024")
#         court    : tribunal (ex: "Tribunal da Relação de Lisboa")

#     Returns JSON:
#         {
#             "status":     "indexado" | "duplicado" | "erro",
#             "mensagem":   str,
#             "hash":       str,
#             "nome_final": str,
#             "n_chunks":   int,
#         }
#     """
#     if request.method != "POST":
#         return JsonResponse({"erro": "Método não permitido."}, status=405)

#     ficheiro = request.FILES.get("ficheiro")
#     if not ficheiro:
#         return JsonResponse({"erro": "Nenhum ficheiro enviado."}, status=400)

#     if not ficheiro.name.lower().endswith(".pdf"):
#         return JsonResponse({"erro": "Apenas ficheiros PDF são aceites."}, status=400)

#     tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
#     try:
#         for bloco in ficheiro.chunks():
#             tmp.write(bloco)
#         tmp.close()

#         metadata = {
#             "type":  request.POST.get("type",  "document"),
#             "year":  request.POST.get("year",  ""),
#             "court": request.POST.get("court", ""),
#         }

#         resultado = registar_e_indexar(
#             path_original       = tmp.name,
#             metadata_utilizador = metadata,
#             chunker             = _chunker,
#             store               = _store,
#         )
#         status_http = 200 if resultado["status"] in ("indexado", "duplicado") else 500
#         return JsonResponse(resultado, status=status_http)

#     except Exception as e:
#         return JsonResponse({"erro": str(e)}, status=500)
#     finally:
#         try:
#             os.unlink(tmp.name)
#         except Exception:
#             pass


# # ---------------------------------------------------------------------------
# # ITIJ views
# # ---------------------------------------------------------------------------

# from itij_scraper import ITIJScraper, TRIBUNAIS as ITIJ_TRIBUNAIS

# _itij = ITIJScraper(timeout=20, delay=0.5)


# @csrf_exempt
# def itij_pesquisar(request):
#     """
#     GET /api/itij/pesquisar/
#     Params:
#         q        : query string
#         tribunal : codigo do tribunal (tre, trl, trp, ...)
#         tipo     : livre | termos | campo | descritor (default: livre)
#         campo    : campo para pesquisa por campo (default: DESCRITORES)
#         operador : operador para pesquisa por campo (default: =)
#         max      : numero maximo de resultados (default: 20)

#     Returns JSON: lista de acordaos ou descritores
#     """
#     q        = request.GET.get("q", "").strip()
#     tribunal = request.GET.get("tribunal", "tre")
#     tipo     = request.GET.get("tipo", "livre")
#     campo    = request.GET.get("campo", "DESCRITORES")
#     operador = request.GET.get("operador", "=")
#     max_r    = min(int(request.GET.get("max", 20)), 50)

#     if not q:
#         return JsonResponse({"erro": "Parâmetro 'q' obrigatório."}, status=400)

#     try:
#         if tipo == "livre":
#             resultados = _itij.pesquisar_livre(q, tribunal, max_r)
#         elif tipo == "termos":
#             termos = [t.strip() for t in q.split(",") if t.strip()]
#             resultados = _itij.pesquisar_termos(termos, tribunal=tribunal,
#                                                 max_resultados=max_r)
#         elif tipo == "campo":
#             resultados = _itij.pesquisar_campo(campo, operador, q, tribunal, max_r)
#         elif tipo == "descritor":
#             resultados = _itij.pesquisar_descritor(q, tribunal, max_r)
#         else:
#             return JsonResponse({"erro": f"Tipo '{tipo}' inválido."}, status=400)

#         return JsonResponse({"resultados": resultados, "total": len(resultados)})

#     except Exception as e:
#         return JsonResponse({"erro": str(e)}, status=500)


# @csrf_exempt
# @require_POST
# def itij_indexar(request):
#     """
#     POST /api/itij/indexar/
#     Pipeline: download HTML -> guardar bruto (acordaos_html/) ->
#               limpar -> texto (acordaos_limpos/) ->
#               LLM classifica blocos -> indexar ChromaDB
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON invalido."}, status=400)

#     urls          = body.get("urls", [])
#     tribunal      = body.get("tribunal", "")
#     acordaos_meta = body.get("acordaos_meta", [])
#     if not urls:
#         return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

#     nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
#     meta_map      = {m["url"]: m for m in acordaos_meta}

#     import re as _re
#     import requests as _req
#     from llm_chunker import LLMChunker

#     llm_chunker = LLMChunker(
#         base_url   =_cfg.llm.base_url,
#         model      =_cfg.llm.model_name,
#         block_size =2200,
#         overlap    =100,
#         temperature=0.0,
#         timeout    =180,
#     )

#     resultados = []
#     for url in urls:
#         try:
#             # 1. Download HTML
#             resp = _req.get(url, timeout=30, headers={
#                 "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
#                 "Accept":          "text/html,application/xhtml+xml",
#                 "Accept-Language": "pt-PT,pt;q=0.9",
#                 "Referer":         "https://www.dgsi.pt/",
#             })
#             if resp.status_code != 200:
#                 raise RuntimeError(f"ITIJ devolveu HTTP {resp.status_code}")
#             resp.encoding = "iso-8859-1"
#             html_content  = resp.text

#             # 2. Nome base
#             proc_match = _re.search(r"/([a-f0-9]{32})", url)
#             proc_id    = proc_match.group(1)[:12] if proc_match else "acordao"
#             nome_base  = f"{tribunal.upper()}_{proc_id}"

#             # 3. Metadados
#             ameta = meta_map.get(url, {})
#             year  = body.get("year", "") or (ameta.get("data", "")[-4:] if ameta.get("data") else "")
#             metadata = {
#                 "type":        body.get("type", "ruling"),
#                 "year":        year,
#                 "court":       nome_tribunal,
#                 "source":      "ITIJ",
#                 "url":         url,
#                 "tribunal_id": tribunal,
#                 "processo":    ameta.get("processo", ""),
#                 "relator":     ameta.get("relator", ""),
#                 "descritores": ", ".join(ameta.get("descritores", [])[:5]),
#             }

#             # 4. Indexar com novo pipeline
#             resultado = registar_e_indexar_itij(
#                 html_content       =html_content,
#                 nome_base          =nome_base,
#                 metadata_utilizador=metadata,
#                 store              =_store,
#                 llm_chunker        =llm_chunker,
#             )
#             resultado["url"] = url
#             resultados.append(resultado)

#         except Exception as e:
#             import traceback
#             print(f"ITIJ ERRO para {url}:")
#             traceback.print_exc()
#             resultados.append({"url": url, "status": "erro", "mensagem": str(e)})

#     indexados  = sum(1 for r in resultados if r["status"] == "indexado")
#     duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
#     erros      = sum(1 for r in resultados if r["status"] == "erro")

#     return JsonResponse({
#         "resultados": resultados,
#         "resumo": {
#             "total": len(urls), "indexados": indexados,
#             "duplicados": duplicados, "erros": erros,
#         }
#     })


# @csrf_exempt
# def itij_sumario(request):
#     """
#     GET /api/itij/sumario/?url=https://dgsi.pt/...
#     Devolve o sumario de um acordao dado o seu URL.
#     Usado pelo frontend para enriquecer progressivamente os resultados.
#     """
#     url = request.GET.get("url", "").strip()
#     if not url:
#         return JsonResponse({"erro": "Parametro url obrigatorio."}, status=400)

#     try:
#         import requests as _req
#         from html_cleaner import limpar_acordao

#         resp = _req.get(url, timeout=15, headers={
#             "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
#             "Accept":          "text/html,application/xhtml+xml",
#             "Accept-Language": "pt-PT,pt;q=0.9",
#             "Referer":         "https://www.dgsi.pt/",
#         })
#         if resp.status_code != 200:
#             return JsonResponse({"sumario": ""})

#         resp.encoding = "iso-8859-1"
#         resultado = limpar_acordao(resp.text)

#         sumario  = resultado.get("sumario", "")
#         metadados = resultado.get("metadados", {})

#         return JsonResponse({
#             "sumario":  sumario[:800] if sumario else "",
#             "decisao":  metadados.get("Decisão", ""),
#             "area":     metadados.get("Área Temática", ""),
#         })

#     except Exception as e:
#         return JsonResponse({"sumario": "", "erro": str(e)})

"""
assistente/views.py

Django views for the AIAA RAG pipeline.

The Retriever and all its components are initialised once when the
Django process starts — not on every request. This keeps the embedding
model in memory and avoids the multi-second startup cost per query.
"""

import json
import os
import tempfile

from django.http import JsonResponse, FileResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from config import load_config, build_embedder, build_store, \
                   build_prompt_builder, build_llm, build_chunker
from retriever import Retriever
from document_generator import DocumentGenerator, CasoDespedimento
from document_registry import registar_e_indexar, registar_e_indexar_itij

# ---------------------------------------------------------------------------
# One-time initialisation — runs when Django starts
# ---------------------------------------------------------------------------

_cfg       = load_config()
_embedder  = build_embedder(_cfg.embedder)
_store     = build_store(_cfg.vector_store, _embedder)
_builder   = build_prompt_builder(_cfg.prompt_builder)
_llm       = build_llm(_cfg.llm)
_chunker   = build_chunker(_cfg.chunker)
_retriever = Retriever(_store, _builder, _llm, _cfg.retriever.n_results)
_generator = DocumentGenerator(_store, _llm)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def index(request):
    """Serve the main chat interface."""
    context = {
        "modelo":   _cfg.llm.model_name,
        "embedder": _cfg.embedder.model_name,
        "n_docs":   _store.count(),
    }
    return render(request, "assistente/index.html", context)


@csrf_exempt
@require_POST
def pergunta(request):
    """
    POST /api/pergunta/
    Body: {"pergunta": "..."}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    q = body.get("pergunta", "").strip()
    if not q:
        return JsonResponse({"erro": "Pergunta vazia."}, status=400)

    if _store.count() == 0:
        return JsonResponse(
            {"erro": "Nenhum documento indexado. Corre primeiro: python indexar.py"},
            status=503,
        )

    result = _retriever.ask(q)

    # Construir mapa hash -> sumario para fontes que nao trazem sumario nos metadados
    # (acórdaos indexados antes do novo pipeline nao tinham sumario nos metadados)
    sumarios_cache = {}
    for s in result.sources:
        h = s["metadata"].get("hash_documento", "")
        if h and not s["metadata"].get("sumario", ""):
            if h not in sumarios_cache:
                try:
                    chunks_sum = _store.search(
                        "sumario acórdão",
                        filters={"hash_documento": h, "section": "sumario"},
                        n=1,
                    )
                    sumarios_cache[h] = chunks_sum[0]["text"][:500] if chunks_sum else ""
                except Exception:
                    sumarios_cache[h] = ""

    return JsonResponse({
        "resposta": result.answer,
        "fontes": [
            {
                "score":    round(s["score"], 2),
                "ficheiro": s["metadata"].get("nome_ficheiro") or s["metadata"].get("filename", "desconhecido"),
                "tipo":     s["metadata"].get("type", ""),
                "ano":      s["metadata"].get("year", ""),
                "data":     s["metadata"].get("data", ""),
                "pagina":   s["metadata"].get("page_start", ""),
                "seccao":   s["metadata"].get("section", ""),
                "processo": s["metadata"].get("processo", ""),
                "relator":  s["metadata"].get("relator", ""),
                "tribunal": s["metadata"].get("court", ""),
                "sumario":  s["metadata"].get("sumario", "") or sumarios_cache.get(s["metadata"].get("hash_documento", ""), ""),
                "texto":    s.get("text", ""),
                "url":      s["metadata"].get("url", ""),
            }
            for s in result.sources
        ],
    })


@csrf_exempt
@require_POST
def gerar_peca(request):
    """
    POST /api/gerar_peca/
    Body: JSON com os campos do CasoDespedimento
    Returns: ficheiro .docx para download
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
        caminho       = _generator.gerar(caso, output_path=tmp.name)
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


@csrf_exempt
def upload_documento(request):
    """
    POST /api/upload/
    multipart/form-data:
        ficheiro : PDF a indexar
        type     : "ruling" | "legislation" | "document"
        year     : ano (ex: "2024")
        court    : tribunal (ex: "Tribunal da Relação de Lisboa")

    Returns JSON:
        {
            "status":     "indexado" | "duplicado" | "erro",
            "mensagem":   str,
            "hash":       str,
            "nome_final": str,
            "n_chunks":   int,
        }
    """
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido."}, status=405)

    ficheiro = request.FILES.get("ficheiro")
    if not ficheiro:
        return JsonResponse({"erro": "Nenhum ficheiro enviado."}, status=400)

    if not ficheiro.name.lower().endswith(".pdf"):
        return JsonResponse({"erro": "Apenas ficheiros PDF são aceites."}, status=400)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        for bloco in ficheiro.chunks():
            tmp.write(bloco)
        tmp.close()

        metadata = {
            "type":  request.POST.get("type",  "document"),
            "year":  request.POST.get("year",  ""),
            "court": request.POST.get("court", ""),
        }

        resultado = registar_e_indexar(
            path_original       = tmp.name,
            metadata_utilizador = metadata,
            chunker             = _chunker,
            store               = _store,
        )
        status_http = 200 if resultado["status"] in ("indexado", "duplicado") else 500
        return JsonResponse(resultado, status=status_http)

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# ITIJ views
# ---------------------------------------------------------------------------

from itij_scraper import ITIJScraper, TRIBUNAIS as ITIJ_TRIBUNAIS

_itij = ITIJScraper(timeout=20, delay=0.5)


@csrf_exempt
def itij_pesquisar(request):
    """
    GET /api/itij/pesquisar/
    Params:
        q        : query string
        tribunal : codigo do tribunal (tre, trl, trp, ...)
        tipo     : livre | termos | campo | descritor (default: livre)
        campo    : campo para pesquisa por campo (default: DESCRITORES)
        operador : operador para pesquisa por campo (default: =)
        max      : numero maximo de resultados (default: 20)

    Returns JSON: lista de acordaos ou descritores
    """
    q        = request.GET.get("q", "").strip()
    tribunal = request.GET.get("tribunal", "tre")
    tipo     = request.GET.get("tipo", "livre")
    campo    = request.GET.get("campo", "DESCRITORES")
    operador = request.GET.get("operador", "=")
    max_r    = min(int(request.GET.get("max", 20)), 50)

    if not q:
        return JsonResponse({"erro": "Parâmetro 'q' obrigatório."}, status=400)

    try:
        if tipo == "livre":
            resultados = _itij.pesquisar_livre(q, tribunal, max_r)
        elif tipo == "termos":
            termos = [t.strip() for t in q.split(",") if t.strip()]
            resultados = _itij.pesquisar_termos(termos, tribunal=tribunal,
                                                max_resultados=max_r)
        elif tipo == "campo":
            resultados = _itij.pesquisar_campo(campo, operador, q, tribunal, max_r)
        elif tipo == "descritor":
            resultados = _itij.pesquisar_descritor(q, tribunal, max_r)
        else:
            return JsonResponse({"erro": f"Tipo '{tipo}' inválido."}, status=400)

        return JsonResponse({"resultados": resultados, "total": len(resultados)})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@csrf_exempt
@require_POST
def itij_indexar(request):
    """
    POST /api/itij/indexar/
    Pipeline: download HTML -> guardar bruto (acordaos_html/) ->
              limpar -> texto (acordaos_limpos/) ->
              LLM classifica blocos -> indexar ChromaDB
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON invalido."}, status=400)

    urls          = body.get("urls", [])
    tribunal      = body.get("tribunal", "")
    acordaos_meta = body.get("acordaos_meta", [])
    if not urls:
        return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

    nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
    meta_map      = {m["url"]: m for m in acordaos_meta}

    import re as _re
    import requests as _req
    from llm_chunker import LLMChunker

    llm_chunker = LLMChunker(
        base_url   =_cfg.llm.base_url,
        model      =_cfg.llm.model_name,
        block_size =2200,
        overlap    =100,
        temperature=0.0,
        timeout    =180,
    )

    resultados = []
    for url in urls:
        try:
            # 1. Download HTML
            resp = _req.get(url, timeout=30, headers={
                "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept":          "text/html,application/xhtml+xml",
                "Accept-Language": "pt-PT,pt;q=0.9",
                "Referer":         "https://www.dgsi.pt/",
            })
            if resp.status_code != 200:
                raise RuntimeError(f"ITIJ devolveu HTTP {resp.status_code}")
            resp.encoding = "iso-8859-1"
            html_content  = resp.text

            # 2. Nome base
            proc_match = _re.search(r"/([a-f0-9]{32})", url)
            proc_id    = proc_match.group(1)[:12] if proc_match else "acordao"
            nome_base  = f"{tribunal.upper()}_{proc_id}"

            # 3. Metadados
            ameta = meta_map.get(url, {})
            year  = body.get("year", "") or (ameta.get("data", "")[-4:] if ameta.get("data") else "")
            metadata = {
                "type":        body.get("type", "ruling"),
                "year":        year,
                "court":       nome_tribunal,
                "source":      "ITIJ",
                "url":         url,
                "tribunal_id": tribunal,
                "processo":    ameta.get("processo", ""),
                "relator":     ameta.get("relator", ""),
                "descritores": ", ".join(ameta.get("descritores", [])[:5]),
            }

            # 4. Indexar com novo pipeline
            resultado = registar_e_indexar_itij(
                html_content       =html_content,
                nome_base          =nome_base,
                metadata_utilizador=metadata,
                store              =_store,
                llm_chunker        =llm_chunker,
            )
            resultado["url"] = url
            resultados.append(resultado)

        except Exception as e:
            import traceback
            print(f"ITIJ ERRO para {url}:")
            traceback.print_exc()
            resultados.append({"url": url, "status": "erro", "mensagem": str(e)})

    indexados  = sum(1 for r in resultados if r["status"] == "indexado")
    duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
    erros      = sum(1 for r in resultados if r["status"] == "erro")

    return JsonResponse({
        "resultados": resultados,
        "resumo": {
            "total": len(urls), "indexados": indexados,
            "duplicados": duplicados, "erros": erros,
        }
    })


@csrf_exempt
def itij_sumario(request):
    """
    GET /api/itij/sumario/?url=https://dgsi.pt/...
    Devolve o sumario de um acordao dado o seu URL.
    Usado pelo frontend para enriquecer progressivamente os resultados.
    """
    url = request.GET.get("url", "").strip()
    if not url:
        return JsonResponse({"erro": "Parametro url obrigatorio."}, status=400)

    try:
        import requests as _req
        from html_cleaner import limpar_acordao

        resp = _req.get(url, timeout=15, headers={
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept":          "text/html,application/xhtml+xml",
            "Accept-Language": "pt-PT,pt;q=0.9",
            "Referer":         "https://www.dgsi.pt/",
        })
        if resp.status_code != 200:
            return JsonResponse({"sumario": ""})

        resp.encoding = "iso-8859-1"
        resultado = limpar_acordao(resp.text)

        sumario  = resultado.get("sumario", "")
        metadados = resultado.get("metadados", {})

        return JsonResponse({
            "sumario":  sumario[:800] if sumario else "",
            "decisao":  metadados.get("Decisão", ""),
            "area":     metadados.get("Área Temática", ""),
        })

    except Exception as e:
        return JsonResponse({"sumario": "", "erro": str(e)})