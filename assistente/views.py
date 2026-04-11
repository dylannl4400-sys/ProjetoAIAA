# # from django.shortcuts import render

# # # Create your views here.

# """
# assistente/views.py

# Django views for the AIAA RAG pipeline.

# The Retriever and all its components are initialised once when the
# Django process starts — not on every request. This keeps the embedding
# model in memory and avoids the multi-second startup cost per query.
# """

# import json

# from django.http import JsonResponse
# from django.shortcuts import render
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_POST

# from config import load_config, build_embedder, build_store, \
#                    build_prompt_builder, build_llm
# from retriever import Retriever

# # ---------------------------------------------------------------------------
# # One-time initialisation — runs when Django starts
# # ---------------------------------------------------------------------------

# _cfg       = load_config()
# _embedder  = build_embedder(_cfg.embedder)
# _store     = build_store(_cfg.vector_store, _embedder)
# _builder   = build_prompt_builder(_cfg.prompt_builder)
# _llm       = build_llm(_cfg.llm)
# _retriever = Retriever(_store, _builder, _llm, _cfg.retriever.n_results)


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

#     Returns:
#         {
#             "resposta": "...",
#             "fontes": [
#                 {"score": 0.82, "ficheiro": "...", "tipo": "...", "ano": "..."},
#                 ...
#             ]
#         }
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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
#             }
#             for s in result.sources
#         ],
#     })

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

# from config import load_config, build_embedder, build_store,                    build_prompt_builder, build_llm
# from retriever import Retriever
# from document_generator import DocumentGenerator, CasoDespedimento

# # ---------------------------------------------------------------------------
# # One-time initialisation — runs when Django starts
# # ---------------------------------------------------------------------------

# _cfg       = load_config()
# _embedder  = build_embedder(_cfg.embedder)
# _store     = build_store(_cfg.vector_store, _embedder)
# _builder   = build_prompt_builder(_cfg.prompt_builder)
# _llm       = build_llm(_cfg.llm)
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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
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
#         caminho = _generator.gerar(caso, output_path=tmp.name)
#         nome_ficheiro = f"carta_cessacao_{caso.nome_trabalhador.replace(' ', '_') or 'documento'}.docx"
#         response = FileResponse(
#             open(caminho, "rb"),
#             as_attachment=True,
#             filename=nome_ficheiro,
#             content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#         )
#         return response
#     except Exception as e:
#         return JsonResponse({"erro": str(e)}, status=500)
#     finally:
#         try:
#             os.unlink(tmp.name)
#         except Exception:
#             pass

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
# from document_registry import registar_e_indexar

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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
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
# from document_registry import registar_e_indexar

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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
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
#     Body: {
#         "urls":     ["https://dgsi.pt/...", ...],
#         "tribunal": "tre",
#         "type":     "ruling",
#         "year":     "2024"
#     }
#     Descarrega e indexa os acordaos seleccionados.
#     Returns: lista de resultados por URL
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     urls     = body.get("urls", [])
#     tribunal = body.get("tribunal", "")
#     if not urls:
#         return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

#     nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
#     resultados    = []

#     for url in urls:
#         try:
#             # Descarregar texto do acordao
#             texto = _itij.descarregar_texto(url)

#             # Guardar temporariamente como txt
#             tmp = tempfile.NamedTemporaryFile(
#                 suffix=".txt", delete=False,
#                 mode="w", encoding="utf-8"
#             )
#             tmp.write(texto)
#             tmp.close()

#             metadata = {
#                 "type":     body.get("type", "ruling"),
#                 "year":     body.get("year", ""),
#                 "court":    nome_tribunal,
#                 "source":   "ITIJ",
#                 "url":      url,
#             }

#             resultado = registar_e_indexar(
#                 path_original       = tmp.name,
#                 metadata_utilizador = metadata,
#                 chunker             = _chunker,
#                 store               = _store,
#             )
#             resultado["url"] = url
#             resultados.append(resultado)

#         except Exception as e:
#             resultados.append({
#                 "url":      url,
#                 "status":   "erro",
#                 "mensagem": str(e),
#             })
#         finally:
#             try:
#                 os.unlink(tmp.name)
#             except Exception:
#                 pass

#     indexados  = sum(1 for r in resultados if r["status"] == "indexado")
#     duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
#     erros      = sum(1 for r in resultados if r["status"] == "erro")

#     return JsonResponse({
#         "resultados": resultados,
#         "resumo": {
#             "total":      len(urls),
#             "indexados":  indexados,
#             "duplicados": duplicados,
#             "erros":      erros,
#         }
#     })

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
# from document_registry import registar_e_indexar

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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
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
#     Body: {
#         "urls":     ["https://dgsi.pt/...", ...],
#         "tribunal": "tre",
#         "type":     "ruling",
#         "year":     "2024"
#     }
#     Descarrega e indexa os acordaos seleccionados.
#     Returns: lista de resultados por URL
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     urls     = body.get("urls", [])
#     tribunal = body.get("tribunal", "")
#     if not urls:
#         return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

#     nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
#     resultados    = []

#     for url in urls:
#         try:
#             # Descarregar HTML do acordao (preserva estrutura para chunking)
#             import requests as _req
#             resp = _req.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
#             resp.encoding = "iso-8859-1"
#             html_content = resp.text

#             # Guardar HTML temporariamente
#             tmp = tempfile.NamedTemporaryFile(
#                 suffix=".html", delete=False,
#                 mode="w", encoding="utf-8"
#             )
#             tmp.write(html_content)
#             tmp.close()

#             metadata = {
#                 "type":     body.get("type", "ruling"),
#                 "year":     body.get("year", ""),
#                 "court":    nome_tribunal,
#                 "source":   "ITIJ",
#                 "url":      url,
#             }

#             # Usar ITIJChunker para chunking estrutural do HTML
#             from itij_chunker import ITIJChunker
#             itij_chunker = ITIJChunker(
#                 chunk_size=_cfg.chunker.chunk_size,
#                 overlap=_cfg.chunker.overlap,
#             )

#             resultado = registar_e_indexar(
#                 path_original       = tmp.name,
#                 metadata_utilizador = metadata,
#                 chunker             = itij_chunker,
#                 store               = _store,
#             )
#             resultado["url"] = url
#             resultados.append(resultado)

#         except Exception as e:
#             resultados.append({
#                 "url":      url,
#                 "status":   "erro",
#                 "mensagem": str(e),
#             })
#         finally:
#             try:
#                 os.unlink(tmp.name)
#             except Exception:
#                 pass

#     indexados  = sum(1 for r in resultados if r["status"] == "indexado")
#     duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
#     erros      = sum(1 for r in resultados if r["status"] == "erro")

#     return JsonResponse({
#         "resultados": resultados,
#         "resumo": {
#             "total":      len(urls),
#             "indexados":  indexados,
#             "duplicados": duplicados,
#             "erros":      erros,
#         }
#     })

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
# from document_registry import registar_e_indexar

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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
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
#     Body: {
#         "urls":     ["https://dgsi.pt/...", ...],
#         "tribunal": "tre",
#         "type":     "ruling",
#         "year":     "2024"
#     }
#     Descarrega e indexa os acordaos seleccionados.
#     Returns: lista de resultados por URL
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     urls          = body.get("urls", [])
#     tribunal      = body.get("tribunal", "")
#     acordaos_meta = body.get("acordaos_meta", [])
#     if not urls:
#         return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

#     nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
#     # Criar mapa URL -> metadados
#     meta_map = {m["url"]: m for m in acordaos_meta}
#     resultados    = []

#     import re as _re
#     import requests as _req
#     from itij_chunker import ITIJChunker

#     itij_chunker = ITIJChunker(
#         chunk_size=_cfg.chunker.chunk_size,
#         overlap=_cfg.chunker.overlap,
#     )

#     for url in urls:
#         tmp_path = None
#         try:
#             # 1. Descarregar HTML do acordao
#             resp = _req.get(url, timeout=30, headers={
#                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
#                 "Accept": "text/html,application/xhtml+xml",
#                 "Accept-Language": "pt-PT,pt;q=0.9",
#                 "Referer": "https://www.dgsi.pt/",
#             })
#             if resp.status_code != 200:
#                 raise RuntimeError(f"ITIJ devolveu HTTP {resp.status_code} para {url}")
#             resp.encoding = "iso-8859-1"
#             html_content  = resp.text

#             # 2. Nome do ficheiro baseado no processo
#             proc_match = _re.search(r"/([a-f0-9]{32})\?OpenDocument", url)
#             proc_id    = proc_match.group(1)[:12] if proc_match else "acordao"
#             trib_id    = tribunal.upper() if tribunal else "TRE"

#             # 3. Guardar HTML em ficheiro temporario permanente (nao auto-apagado)
#             tmp_path = os.path.join(
#                 tempfile.gettempdir(),
#                 f"{trib_id}_{proc_id}.html"
#             )
#             with open(tmp_path, "w", encoding="utf-8") as f:
#                 f.write(html_content)

#             # 4. Metadados do acordao
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

#             # 5. Indexar com ITIJChunker
#             resultado = registar_e_indexar(
#                 path_original       = tmp_path,
#                 metadata_utilizador = metadata,
#                 chunker             = itij_chunker,
#                 store               = _store,
#             )
#             resultado["url"] = url
#             resultados.append(resultado)

#         except Exception as e:
#             import traceback
#             print(f"ITIJ ERRO para {url}:")
#             traceback.print_exc()
#             resultados.append({
#                 "url":      url,
#                 "status":   "erro",
#                 "mensagem": str(e),
#             })
#         finally:
#             # Apagar ficheiro temporario so apos indexacao
#             if tmp_path and os.path.exists(tmp_path):
#                 try:
#                     os.unlink(tmp_path)
#                 except Exception:
#                     pass

#     indexados  = sum(1 for r in resultados if r["status"] == "indexado")
#     duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
#     erros      = sum(1 for r in resultados if r["status"] == "erro")

#     return JsonResponse({
#         "resultados": resultados,
#         "resumo": {
#             "total":      len(urls),
#             "indexados":  indexados,
#             "duplicados": duplicados,
#             "erros":      erros,
#         }
#     })

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
# from document_registry import registar_e_indexar

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

#     return JsonResponse({
#         "resposta": result.answer,
#         "fontes": [
#             {
#                 "score":    round(s["score"], 2),
#                 "ficheiro": s["metadata"].get("filename", "desconhecido"),
#                 "tipo":     s["metadata"].get("type", ""),
#                 "ano":      s["metadata"].get("year", ""),
#                 "pagina":   s["metadata"].get("page_start", ""),
#                 "seccao":   s["metadata"].get("section", ""),
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
#     Body: {
#         "urls":     ["https://dgsi.pt/...", ...],
#         "tribunal": "tre",
#         "type":     "ruling",
#         "year":     "2024"
#     }
#     Descarrega e indexa os acordaos seleccionados.
#     Returns: lista de resultados por URL
#     """
#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     urls          = body.get("urls", [])
#     tribunal      = body.get("tribunal", "")
#     acordaos_meta = body.get("acordaos_meta", [])
#     if not urls:
#         return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

#     nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
#     # Criar mapa URL -> metadados
#     meta_map = {m["url"]: m for m in acordaos_meta}
#     resultados    = []

#     import re as _re
#     import requests as _req
#     from itij_chunker import ITIJChunker, extrair_texto_limpo
#     from hashlib import sha256 as _sha256

#     # Pastas para guardar acordaos
#     BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     DIR_RAW       = os.path.join(BASE_DIR, "acordaos_raw")
#     DIR_LIMPOS    = os.path.join(BASE_DIR, "acordaos_limpos")
#     os.makedirs(DIR_RAW,    exist_ok=True)
#     os.makedirs(DIR_LIMPOS, exist_ok=True)

#     itij_chunker = ITIJChunker(
#         chunk_size   = _cfg.chunker.chunk_size,
#         overlap      = _cfg.chunker.overlap,
#         llm_base_url = _cfg.llm.base_url,
#         llm_model    = _cfg.llm.model_name,
#     )

#     for url in urls:
#         try:
#             # 1. Descarregar HTML do acordao
#             resp = _req.get(url, timeout=30, headers={
#                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
#                 "Accept":     "text/html,application/xhtml+xml",
#                 "Accept-Language": "pt-PT,pt;q=0.9",
#                 "Referer":    "https://www.dgsi.pt/",
#             })
#             if resp.status_code != 200:
#                 raise RuntimeError(f"ITIJ devolveu HTTP {resp.status_code}")
#             resp.encoding = "iso-8859-1"
#             html_content  = resp.text

#             # 2. Hash do HTML bruto para deduplicacao e nome do ficheiro
#             hash_doc  = _sha256(html_content.encode("utf-8")).hexdigest()
#             hash_curto = hash_doc[:8]
#             trib_id   = tribunal.upper() if tribunal else "TRE"
#             proc_match = _re.search(r"/([a-f0-9]{32})\?OpenDocument", url)
#             proc_id    = proc_match.group(1)[:12] if proc_match else "acordao"
#             nome_base  = f"{hash_curto}_{trib_id}_{proc_id}"

#             # 3. Guardar HTML bruto (acordaos_raw/)
#             path_raw = os.path.join(DIR_RAW, f"{nome_base}.html")
#             if not os.path.exists(path_raw):
#                 with open(path_raw, "w", encoding="utf-8") as f:
#                     f.write(html_content)

#             # 4. Extrair e guardar texto limpo (acordaos_limpos/)
#             texto_limpo = extrair_texto_limpo(html_content)
#             path_limpo  = os.path.join(DIR_LIMPOS, f"{nome_base}.txt")
#             if not os.path.exists(path_limpo):
#                 with open(path_limpo, "w", encoding="utf-8") as f:
#                     f.write(texto_limpo)

#             # 5. Metadados do acordao
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

#             # 6. Indexar — passa o HTML directamente ao ITIJChunker
#             #    document_registry usa hash_doc para deduplicacao
#             resultado = registar_e_indexar(
#                 path_original       = path_raw,
#                 metadata_utilizador = metadata,
#                 chunker             = itij_chunker,
#                 store               = _store,
#             )
#             resultado["url"] = url
#             resultados.append(resultado)

#         except Exception as e:
#             import traceback
#             print(f"ITIJ ERRO para {url}:")
#             traceback.print_exc()
#             resultados.append({
#                 "url":      url,
#                 "status":   "erro",
#                 "mensagem": str(e),
#             })

#     indexados  = sum(1 for r in resultados if r["status"] == "indexado")
#     duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
#     erros      = sum(1 for r in resultados if r["status"] == "erro")

#     return JsonResponse({
#         "resultados": resultados,
#         "resumo": {
#             "total":      len(urls),
#             "indexados":  indexados,
#             "duplicados": duplicados,
#             "erros":      erros,
#         }
#     })

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

    return JsonResponse({
        "resposta": result.answer,
        "fontes": [
            {
                "score":    round(s["score"], 2),
                "ficheiro": s["metadata"].get("filename", "desconhecido"),
                "tipo":     s["metadata"].get("type", ""),
                "ano":      s["metadata"].get("year", ""),
                "pagina":   s["metadata"].get("page_start", ""),
                "seccao":   s["metadata"].get("section", ""),
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