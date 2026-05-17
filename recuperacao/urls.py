# from django.urls import path
# from . import views

# urlpatterns = [
#     path("",                                        views.index,            name="index"),
#     path("api/pergunta/",                           views.pergunta,         name="pergunta"),
#     path("api/conversas/",                          views.conversas_listar, name="conversas_listar"),
#     path("api/conversas/nova/",                     views.conversa_nova,    name="conversa_nova"),
#     path("api/conversas/<int:conversa_id>/",        views.conversa_detalhe, name="conversa_detalhe"),
#     path("api/conversas/<int:conversa_id>/apagar/", views.conversa_apagar,  name="conversa_apagar"),
# ]

"""recuperacao/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path("api/auth/registar/",              views.auth_registar,    name="auth_registar"),
    path("api/auth/login/",                 views.auth_login,       name="auth_login"),
    path("",                              views.index,            name="index"),
    path("api/pergunta/",                 views.pergunta,         name="pergunta"),
    path("api/conversas/",                views.conversas_listar, name="conversas_listar"),
    path("api/conversas/nova/",           views.conversa_nova,    name="conversa_nova"),
    path("api/conversas/<int:conversa_id>/",        views.conversa_detalhe, name="conversa_detalhe"),
    path("api/conversas/<int:conversa_id>/apagar/", views.conversa_apagar,  name="conversa_apagar"),
    path("api/feedback/fonte/",           views.api_feedback_fonte, name="api_feedback_fonte"),
]