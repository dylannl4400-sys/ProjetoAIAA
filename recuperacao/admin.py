# recuperacao/admin.py
from django.contrib import admin
from .models import Utilizador, Conversa, Mensagem

@admin.register(Utilizador)
class UtilizadorAdmin(admin.ModelAdmin):
    list_display  = ["nome", "email", "criado_em", "ultimo_login"]
    search_fields = ["nome", "email"]

@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display  = ["titulo", "utilizador", "criada_em", "alterada_em"]
    list_filter   = ["utilizador"]
    search_fields = ["titulo"]

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display  = ["papel", "conversa", "criada_em"]
    list_filter   = ["papel"]