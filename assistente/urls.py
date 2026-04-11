from django.urls import path
from . import views

# urlpatterns = [
#     path("",              views.index,    name="index"),
#     path("api/pergunta/", views.pergunta, name="pergunta"),
# ]
# urlpatterns = [
#     path("",                  views.index,      name="index"),
#     path("api/pergunta/",     views.pergunta,   name="pergunta"),
#     path("api/gerar_peca/",   views.gerar_peca, name="gerar_peca"),
# ]
# urlpatterns = [
#     path("",                    views.index,            name="index"),
#     path("api/pergunta/",       views.pergunta,         name="pergunta"),
#     path("api/gerar_peca/",     views.gerar_peca,       name="gerar_peca"),
#     path("api/upload/",         views.upload_documento, name="upload_documento"),
# ]

urlpatterns = [
    path("",                      views.index,            name="index"),
    path("api/pergunta/",         views.pergunta,         name="pergunta"),
    path("api/gerar_peca/",       views.gerar_peca,       name="gerar_peca"),
    path("api/upload/",           views.upload_documento, name="upload_documento"),
    path("api/itij/pesquisar/",   views.itij_pesquisar,   name="itij_pesquisar"),
    path("api/itij/indexar/",     views.itij_indexar,     name="itij_indexar"),
]
 