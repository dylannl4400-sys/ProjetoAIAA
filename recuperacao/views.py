# """
# recuperacao/views.py

# Responsabilidade: RAG — receber questão, recuperar chunks, gerar resposta.
# Também gere o histórico de conversas.
# """
# import json

# from django.http  import JsonResponse
# from django.shortcuts import render
# from django.views.decorators.csrf import csrf_exempt

# from recuperacao.models import Conversa, Mensagem
# from aiaa_init import get_cfg, get_store, get_retriever, ITIJ_TRIBUNAIS


# # ---------------------------------------------------------------------------
# # Interface principal
# # ---------------------------------------------------------------------------

# def index(request):
#     """GET / — interface principal com todos os separadores."""
#     conversas = Conversa.objects.all()[:50]
#     return render(request, "recuperacao/index.html", {
#         "modelo":    get_cfg().llm.model_name,
#         "embedder":  get_cfg().embedder.model_name,
#         "n_docs":    get_store().count(),
#         "conversas": conversas,
#     })


# # ---------------------------------------------------------------------------
# # RAG — questão jurídica
# # ---------------------------------------------------------------------------

# @csrf_exempt
# def pergunta(request):
#     """
#     POST /api/pergunta/
#     Body: { "pergunta": str, "conversa_id": int | null }
#     """
#     if request.method != "POST":
#         return JsonResponse({"erro": "POST obrigatório."}, status=405)

#     try:
#         body = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"erro": "JSON inválido."}, status=400)

#     q           = body.get("pergunta", "").strip()
#     conversa_id = body.get("conversa_id")

#     if not q:
#         return JsonResponse({"erro": "Pergunta vazia."}, status=400)

#     if get_store().count() == 0:
#         return JsonResponse(
#             {"erro": "Nenhum documento indexado. Indexa primeiro acórdãos no separador ITIJ."},
#             status=503,
#         )

#     # Obter ou criar conversa
#     if conversa_id:
#         conversa, _ = Conversa.objects.get_or_create(
#             id=conversa_id, defaults={"titulo": "Nova conversa"}
#         )
#     else:
#         conversa = Conversa.objects.create(titulo="Nova conversa")

#     Mensagem.objects.create(conversa=conversa, papel="user", texto=q)

#     # RAG
#     result = get_retriever().ask(q)

#     # Enriquecer fontes com sumário (de chunks já indexados)
#     sumarios_cache = {}
#     for s in result.sources:
#         h = s["metadata"].get("hash_documento", "")
#         if h and not s["metadata"].get("sumario", ""):
#             if h not in sumarios_cache:
#                 try:
#                     from ingestao.models import AcordaoIndexado
#                     registo = AcordaoIndexado.objects.filter(hash_documento__startswith=h[:8]).first()
#                     sumarios_cache[h] = registo.sumario[:500] if registo else ""
#                 except Exception:
#                     sumarios_cache[h] = ""

#     fontes = [
#         {
#             "score":    round(s["score"], 2),
#             "ficheiro": s["metadata"].get("nome_ficheiro") or s["metadata"].get("filename", "desconhecido"),
#             "tipo":     s["metadata"].get("type", ""),
#             "ano":      s["metadata"].get("year", ""),
#             "seccao":   s["metadata"].get("section", ""),
#             "processo": s["metadata"].get("processo", ""),
#             "relator":  s["metadata"].get("relator", ""),
#             "tribunal": s["metadata"].get("court", ""),
#             "sumario":  s["metadata"].get("sumario", "") or sumarios_cache.get(s["metadata"].get("hash_documento", ""), ""),
#             "url":      s["metadata"].get("url", ""),
#         }
#         for s in result.sources
#     ]

#     Mensagem.objects.create(
#         conversa=conversa, papel="assistant", texto=result.answer, fontes=fontes
#     )

#     # Título automático com a primeira pergunta
#     if conversa.mensagens.filter(papel="user").count() == 1:
#         conversa.titulo = q[:80] + ("…" if len(q) > 80 else "")
#         conversa.save()

#     return JsonResponse({
#         "resposta":         result.answer,
#         "fontes":           fontes,
#         "conversa_id":      conversa.id,
#         "conversa_titulo":  conversa.titulo,
#     })


# # ---------------------------------------------------------------------------
# # Conversas
# # ---------------------------------------------------------------------------

# @csrf_exempt
# def conversas_listar(request):
#     """GET /api/conversas/"""
#     conversas = Conversa.objects.all()[:50]
#     return JsonResponse({
#         "conversas": [
#             {
#                 "id":          c.id,
#                 "titulo":      c.titulo,
#                 "alterada_em": c.alterada_em.strftime("%d/%m/%Y %H:%M"),
#             }
#             for c in conversas
#         ]
#     })


# @csrf_exempt
# def conversa_detalhe(request, conversa_id):
#     """GET /api/conversas/<id>/"""
#     try:
#         conversa = Conversa.objects.get(id=conversa_id)
#     except Conversa.DoesNotExist:
#         return JsonResponse({"erro": "Não encontrada."}, status=404)
#     return JsonResponse({
#         "id":     conversa.id,
#         "titulo": conversa.titulo,
#         "mensagens": [
#             {
#                 "papel":     m.papel,
#                 "texto":     m.texto,
#                 "fontes":    m.fontes,
#                 "criada_em": m.criada_em.strftime("%H:%M"),
#             }
#             for m in conversa.mensagens.all()
#         ]
#     })


# @csrf_exempt
# def conversa_nova(request):
#     """POST /api/conversas/nova/"""
#     c = Conversa.objects.create(titulo="Nova conversa")
#     return JsonResponse({"id": c.id, "titulo": c.titulo})


# @csrf_exempt
# def conversa_apagar(request, conversa_id):
#     """DELETE /api/conversas/<id>/apagar/"""
#     try:
#         Conversa.objects.get(id=conversa_id).delete()
#         return JsonResponse({"ok": True})
#     except Conversa.DoesNotExist:
#         return JsonResponse({"erro": "Não encontrada."}, status=404)

"""
recuperacao/views.py

Responsabilidade: RAG — receber questão, recuperar chunks, gerar resposta.
Também gere o histórico de conversas.
"""
import json

from django.http  import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from recuperacao.models import Conversa, Mensagem
from aiaa_init import get_cfg, get_store, get_retriever, ITIJ_TRIBUNAIS


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------

def index(request):
    """GET / — interface principal com todos os separadores."""
    conversas = Conversa.objects.all()[:50]
    return render(request, "recuperacao/index.html", {
        "modelo":    get_cfg().llm.model_name,
        "embedder":  get_cfg().embedder.model_name,
        "n_docs":    get_store().count(),
        "conversas": conversas,
    })


# ---------------------------------------------------------------------------
# RAG — questão jurídica
# ---------------------------------------------------------------------------

@csrf_exempt
def pergunta(request):
    """
    POST /api/pergunta/
    Body: { "pergunta": str, "conversa_id": int | null }
    """
    if request.method != "POST":
        return JsonResponse({"erro": "POST obrigatório."}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    q            = body.get("pergunta", "").strip()
    conversa_id  = body.get("conversa_id")
    utilizador_id = body.get("utilizador_id")
    n_results     = int(body.get("n_results", 10))

    if not q:
        return JsonResponse({"erro": "Pergunta vazia."}, status=400)

    if get_store().count() == 0:
        return JsonResponse(
            {"erro": "Nenhum documento indexado. Indexa primeiro acórdãos no separador ITIJ."},
            status=503,
        )

    # Obter ou criar conversa
    uid = utilizador_id or None
    if conversa_id:
        conversa, _ = Conversa.objects.get_or_create(
            id=conversa_id, defaults={"titulo": "Nova conversa", "utilizador_id": uid}
        )
    else:
        conversa = Conversa.objects.create(titulo="Nova conversa", utilizador_id=uid)

    Mensagem.objects.create(conversa=conversa, papel="user", texto=q)

    # RAG - Recuperação inicial
    result = get_retriever().ask(q, n_results=n_results)
    
    # --- Passo 2: Otimização por Feedback (Human-in-the-loop) ---
    from recuperacao.models import FonteFeedback
    from django.db.models import Count, Sum

    # Obter os IDs das fontes recuperadas pelo vector store
    ids_recuperados = []
    for s in result.sources:
        fid = s["metadata"].get("processo") or s["metadata"].get("nome_ficheiro") or s["metadata"].get("filename")
        if fid: ids_recuperados.append(fid)

    # Consultar reputação destas fontes na BD (soma de relevância)
    reputacao = {
        fb['fonte_id']: fb['total_rel'] 
        for fb in FonteFeedback.objects.filter(fonte_id__in=ids_recuperados)
                                       .values('fonte_id')
                                       .annotate(total_rel=Sum('relevancia'))
    }

    # Aplicar o "Boost" no score vetorial baseado na reputação
    # Fontes com Thumbs-up (total_rel > 0) sobem no ranking
    fontes_enriquecidas = []
    for s in result.sources:
        fid = s["metadata"].get("processo") or s["metadata"].get("nome_ficheiro") or s["metadata"].get("filename")
        boost = reputacao.get(fid, 0) * 0.05 # Cada thumb-up dá +5% de relevância
        
        # Não deixar o score passar de 1.0 ou ficar abaixo de 0
        novo_score = min(1.0, max(0.0, s["score"] + boost))
        
        fontes_enriquecidas.append({
            "score":    round(novo_score, 2),
            "original_score": s["score"],
            "feedback_boost": boost,
            "ficheiro": s["metadata"].get("nome_ficheiro") or s["metadata"].get("filename", "desconhecido"),
            "tipo":     s["metadata"].get("type", ""),
            "ano":      s["metadata"].get("year", ""),
            "data":     s["metadata"].get("data", ""),
            "seccao":   s["metadata"].get("section", ""),
            "processo": s["metadata"].get("processo", ""),
            "relator":  s["metadata"].get("relator", ""),
            "tribunal": s["metadata"].get("court", ""),
            "sumario":  s["metadata"].get("sumario", ""), # Será preenchido abaixo se vazio
            "texto":    s.get("text", ""),
            "hash":     s["metadata"].get("hash_documento", ""),
            "url":      s["metadata"].get("url", ""),
        })

    # Ordenar novamente por score (agora com o feedback aplicado)
    fontes_enriquecidas.sort(key=lambda x: x["score"], reverse=True)

    # Enriquecer fontes com sumário (de chunks já indexados)
    sumarios_cache = {}
    for f in fontes_enriquecidas:
        h = f["hash"]
        if h and not f["sumario"]:
            if h not in sumarios_cache:
                try:
                    from ingestao.models import AcordaoIndexado
                    registo = AcordaoIndexado.objects.filter(hash_documento__startswith=h[:8]).first()
                    sumarios_cache[h] = registo.sumario[:500] if registo else ""
                except Exception:
                    sumarios_cache[h] = ""
            f["sumario"] = sumarios_cache.get(h, "")

    fontes = fontes_enriquecidas

    m_asst = Mensagem.objects.create(
        conversa=conversa, papel="assistant", texto=result.answer, fontes=fontes
    )

    # Título automático com a primeira pergunta
    if conversa.mensagens.filter(papel="user").count() == 1:
        conversa.titulo = q[:80] + ("…" if len(q) > 80 else "")
        conversa.save()

    return JsonResponse({
        "mensagem_id":      m_asst.id,
        "resposta":         result.answer,
        "fontes":           fontes,
        "conversa_id":      conversa.id,
        "conversa_titulo":  conversa.titulo,
    })


# ---------------------------------------------------------------------------
# Conversas
# ---------------------------------------------------------------------------

@csrf_exempt
def conversas_listar(request):
    """GET /api/conversas/"""
    conversas = Conversa.objects.all()[:50]
    return JsonResponse({
        "conversas": [
            {
                "id":          c.id,
                "titulo":      c.titulo,
                "alterada_em": c.alterada_em.strftime("%d/%m/%Y %H:%M"),
            }
            for c in conversas
        ]
    })


@csrf_exempt
def conversa_detalhe(request, conversa_id):
    """GET /api/conversas/<id>/"""
    try:
        conversa = Conversa.objects.get(id=conversa_id)
    except Conversa.DoesNotExist:
        return JsonResponse({"erro": "Não encontrada."}, status=404)
    
    msgs = []
    for m in conversa.mensagens.all():
        # Obter feedback das fontes desta mensagem
        feedbacks = {f.fonte_id: {"relevancia": f.relevancia, "removida": f.removida} 
                     for f in m.feedbacks.all()}
        msgs.append({
            "id":        m.id,
            "papel":     m.papel,
            "texto":     m.texto,
            "fontes":    m.fontes,
            "feedbacks": feedbacks,
            "criada_em": m.criada_em.strftime("%H:%M"),
        })

    return JsonResponse({
        "id":     conversa.id,
        "titulo": conversa.titulo,
        "mensagens": msgs
    })


@csrf_exempt
def conversa_nova(request):
    """POST /api/conversas/nova/"""
    c = Conversa.objects.create(titulo="Nova conversa")
    return JsonResponse({"id": c.id, "titulo": c.titulo})


@csrf_exempt
def conversa_apagar(request, conversa_id):
    """DELETE /api/conversas/<id>/apagar/"""
    try:
        Conversa.objects.get(id=conversa_id).delete()
        return JsonResponse({"ok": True})
    except Conversa.DoesNotExist:
        return JsonResponse({"erro": "Não encontrada."}, status=404)


# ---------------------------------------------------------------------------
# Autenticação simples (sem Django Auth completo)
# ---------------------------------------------------------------------------

import hashlib

def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


@csrf_exempt
def auth_registar(request):
    """POST /api/auth/registar/"""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    nome  = body.get("nome", "").strip()
    email = body.get("email", "").strip().lower()
    senha = body.get("senha", "")

    if not nome or not email or not senha:
        return JsonResponse({"erro": "Preenche todos os campos."}, status=400)
    if len(senha) < 6:
        return JsonResponse({"erro": "Senha deve ter pelo menos 6 caracteres."}, status=400)

    from recuperacao.models import Utilizador
    if Utilizador.objects.filter(email=email).exists():
        return JsonResponse({"erro": "Email já registado."}, status=400)

    u = Utilizador.objects.create(
        nome       = nome,
        email      = email,
        senha_hash = _hash_senha(senha),
    )
    return JsonResponse({"id": u.id, "nome": u.nome, "email": u.email})


@csrf_exempt
def auth_login(request):
    """POST /api/auth/login/"""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    email = body.get("email", "").strip().lower()
    senha = body.get("senha", "")

    from recuperacao.models import Utilizador
    from django.utils import timezone
    try:
        u = Utilizador.objects.get(email=email)
    except Utilizador.DoesNotExist:
        return JsonResponse({"erro": "Email ou senha incorrectos."}, status=401)

    if u.senha_hash != _hash_senha(senha):
        return JsonResponse({"erro": "Email ou senha incorrectos."}, status=401)

    u.ultimo_login = timezone.now()
    u.save()
    return JsonResponse({"id": u.id, "nome": u.nome, "email": u.email})


@csrf_exempt
def api_feedback_fonte(request):
    """
    POST /api/feedback/fonte/
    Body: { "mensagem_id": int, "fonte_id": str, "relevancia": int, "removida": bool }
    """
    if request.method != "POST":
        return JsonResponse({"erro": "POST obrigatório."}, status=405)
    
    try:
        body = json.loads(request.body)
        mid  = body.get("mensagem_id")
        fid  = body.get("fonte_id")
        rel  = body.get("relevancia")
        rem  = body.get("removida")
        
        if not mid or not fid:
            return JsonResponse({"erro": "mensagem_id e fonte_id obrigatórios."}, status=400)
        
        from recuperacao.models import FonteFeedback, Mensagem
        msg = Mensagem.objects.get(id=mid)
        
        fb, created = FonteFeedback.objects.get_or_create(
            mensagem=msg, 
            fonte_id=fid
        )
        
        if rel is not None: fb.relevancia = int(rel)
        if rem is not None: fb.removida = bool(rem)
        fb.save()
        
        return JsonResponse({"ok": True, "id": fb.id})
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Conversas filtradas por utilizador
# ---------------------------------------------------------------------------

def conversas_listar(request):
    """GET /api/conversas/?utilizador_id=<id>"""
    from recuperacao.models import Conversa
    uid = request.GET.get("utilizador_id")
    qs  = Conversa.objects.filter(utilizador_id=uid) if uid else Conversa.objects.filter(utilizador__isnull=True)
    return JsonResponse({
        "conversas": [
            {"id": c.id, "titulo": c.titulo, "alterada_em": c.alterada_em.strftime("%d/%m/%Y %H:%M")}
            for c in qs[:50]
        ]
    })