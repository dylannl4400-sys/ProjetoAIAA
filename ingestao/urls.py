from django.urls import path
from . import views

urlpatterns = [
    path("pesquisar/",  views.itij_pesquisar,    name="itij_pesquisar"),
    path("indexar/",    views.itij_indexar,       name="itij_indexar"),
    path("sumario/",    views.itij_sumario,       name="itij_sumario"),
    path("acordaos/",   views.acordaos_indexados, name="acordaos_indexados"),
]