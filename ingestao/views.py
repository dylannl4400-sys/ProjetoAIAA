"""
ingestao/views.py

Responsabilidade: tudo o que tem a ver com obter e indexar documentos.
    - Pesquisar no ITIJ
    - Indexar acórdãos seleccionados
    - Buscar sumário em background
    - Upload manual de PDFs (se mantido)
"""
import json
import re as _re

import requests as _req
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from document_registry import registar_e_indexar_itij
from llm_chunker import LLMChunker
from ingestao.models import AcordaoIndexado

# Importar singletons do projecto (inicializados uma vez)
from aiaa_init import get_cfg, get_store, get_itij, ITIJ_TRIBUNAIS


# ---------------------------------------------------------------------------
# Pesquisar ITIJ
# ---------------------------------------------------------------------------

def itij_pesquisar(request):
    """
    GET /ingestao/pesquisar/?q=&tribunal=tre&tipo=livre&max=50
    """
    q        = request.GET.get("q", "").strip()
    tribunal = request.GET.get("tribunal", "tre").strip()
    tipo     = request.GET.get("tipo", "livre").strip()
    campo    = request.GET.get("campo", "DESCRITORES")
    operador = request.GET.get("operador", "=")
    max_r    = int(request.GET.get("max", 9999))

    if not q:
        return JsonResponse({"erro": "Parâmetro 'q' obrigatório."}, status=400)

    try:
        if tipo == "livre":
            resultados = get_itij().pesquisar_livre(q, tribunal, max_r)
        elif tipo == "termos":
            termos = [t.strip() for t in q.split(",") if t.strip()]
            resultados = get_itij().pesquisar_termos(termos, tribunal=tribunal, max_resultados=max_r)
        elif tipo == "campo":
            resultados = get_itij().pesquisar_campo(campo, operador, q, tribunal, max_r)
        elif tipo == "descritor":
            resultados = get_itij().pesquisar_descritor(q, tribunal, max_r)
        else:
            return JsonResponse({"erro": f"Tipo '{tipo}' inválido."}, status=400)

        return JsonResponse({"resultados": resultados, "total": len(resultados)})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Indexar acórdãos seleccionados
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def itij_indexar(request):
    """
    POST /ingestao/indexar/
    Body: { urls, tribunal, acordaos_meta, type, year }
    Pipeline:
        1. Download HTML
        2. Guardar em acordaos_html/
        3. Limpar → acordaos_limpos/
        4. LLM classifica blocos em secções
        5. Indexar ChromaDB
        6. Guardar registo em AcordaoIndexado (BD)
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    urls          = body.get("urls", [])
    tribunal      = body.get("tribunal", "")
    acordaos_meta = body.get("acordaos_meta", [])

    if not urls:
        return JsonResponse({"erro": "Lista de URLs vazia."}, status=400)

    nome_tribunal = ITIJ_TRIBUNAIS.get(tribunal, {}).get("nome", tribunal)
    meta_map      = {m["url"]: m for m in acordaos_meta}

    llm_chunker = LLMChunker(
        base_url   =get_cfg().llm.base_url,
        model      =get_cfg().llm.model_name,
        block_size =2200,
        overlap    =100,
        temperature=0.0,
        timeout    =180,
    )

    resultados = []
    for url in urls:
        try:
            resp = _req.get(url, timeout=30, headers={
                "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept":          "text/html,application/xhtml+xml",
                "Accept-Language": "pt-PT,pt;q=0.9",
                "Referer":         "https://www.dgsi.pt/",
            })
            if resp.status_code != 200:
                raise RuntimeError(f"ITIJ devolveu HTTP {resp.status_code}")
            resp.encoding = "iso-8859-1"
            html_content  = resp.text

            proc_match = _re.search(r"/([a-f0-9]{32})", url)
            proc_id    = proc_match.group(1)[:12] if proc_match else "acordao"
            nome_base  = f"{tribunal.upper()}_{proc_id}"

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

            resultado = registar_e_indexar_itij(
                html_content       =html_content,
                nome_base          =nome_base,
                metadata_utilizador=metadata,
                store              =get_store(),
                llm_chunker        =llm_chunker,
            )

            # Guardar registo na BD Django
            if resultado["status"] == "indexado":
                from html_cleaner import limpar_acordao
                res_limpeza = limpar_acordao(html_content)
                AcordaoIndexado.objects.get_or_create(
                    hash_documento=resultado["hash"],
                    defaults={
                        "processo":      ameta.get("processo", ""),
                        "relator":       ameta.get("relator", ""),
                        "tribunal_id":   tribunal,
                        "tribunal_nome": nome_tribunal,
                        "data_acordao":  ameta.get("data", ""),
                        "descritores":   ", ".join(ameta.get("descritores", [])),
                        "url":           url,
                        "nome_html":     resultado.get("nome_final", ""),
                        "n_chunks":      resultado["n_chunks"],
                        "sumario":       res_limpeza.get("sumario", "")[:1000],
                    }
                )

            resultado["url"] = url
            resultados.append(resultado)

        except Exception as e:
            import traceback
            traceback.print_exc()
            resultados.append({"url": url, "status": "erro", "mensagem": str(e)})

    indexados  = sum(1 for r in resultados if r["status"] == "indexado")
    duplicados = sum(1 for r in resultados if r["status"] == "duplicado")
    erros      = sum(1 for r in resultados if r["status"] == "erro")

    return JsonResponse({
        "resultados": resultados,
        "resumo": {"total": len(urls), "indexados": indexados,
                   "duplicados": duplicados, "erros": erros},
    })


# ---------------------------------------------------------------------------
# Sumário em background
# ---------------------------------------------------------------------------

@csrf_exempt
def itij_sumario(request):
    """
    GET /ingestao/sumario/?url=...
    Devolve sumário de um acórdão sem o indexar.
    Usado pelo frontend para enriquecer progressivamente os resultados.
    """
    url = request.GET.get("url", "").strip()
    if not url:
        return JsonResponse({"erro": "url obrigatório."}, status=400)

    # Verificar primeiro se já está indexado (mais rápido)
    hash_local = None
    try:
        # Tentar pelo URL nos registos existentes
        registo = AcordaoIndexado.objects.filter(url=url).first()
        if registo and registo.sumario:
            return JsonResponse({"sumario": registo.sumario[:800]})
    except Exception:
        pass

    try:
        from html_cleaner import limpar_acordao
        resp = _req.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer":    "https://www.dgsi.pt/",
        })
        if resp.status_code != 200:
            return JsonResponse({"sumario": ""})
        resp.encoding = "iso-8859-1"
        resultado     = limpar_acordao(resp.text)
        sumario       = resultado.get("sumario", "")
        metadados     = resultado.get("metadados", {})
        return JsonResponse({
            "sumario": sumario[:800] if sumario else "",
            "decisao": metadados.get("decisao", ""),
        })
    except Exception as e:
        return JsonResponse({"sumario": "", "erro": str(e)})


# ---------------------------------------------------------------------------
# Lista de acórdãos indexados
# ---------------------------------------------------------------------------

def acordaos_indexados(request):
    """
    GET /ingestao/acordaos/
    Lista todos os acórdãos indexados na BD.
    """
    acordaos = AcordaoIndexado.objects.all()[:200]
    return JsonResponse({
        "acordaos": [
            {
                "id":           a.id,
                "hash":         a.hash_documento[:8],
                "processo":     a.processo,
                "relator":      a.relator,
                "tribunal":     a.tribunal_id,
                "data":         a.data_acordao,
                "n_chunks":     a.n_chunks,
                "indexado_em":  a.indexado_em.strftime("%d/%m/%Y %H:%M"),
            }
            for a in acordaos
        ],
        "total": AcordaoIndexado.objects.count(),
    })