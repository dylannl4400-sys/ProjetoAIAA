from django.urls import path
from . import views

urlpatterns = [
    path("gerar/",     views.gerar_peca,       name="gerar_peca"),
    path("templates/", views.templates_listar, name="templates_listar"),
]