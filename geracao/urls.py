# from django.urls import path
# from . import views

# urlpatterns = [
#     path("gerar/",     views.gerar_peca,       name="gerar_peca"),
#     path("templates/", views.templates_listar, name="templates_listar"),
# ]

"""geracao/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path("gerar/",     views.gerar_peca,     name="gerar_peca"),
    path("gerar-rag/", views.gerar_peca_rag, name="gerar_peca_rag"),
    path("templates/", views.templates_listar, name="templates_listar"),
]