from django.contrib import admin
from .models import PecaGerada, Template


@admin.register(PecaGerada)
class PecaAdmin(admin.ModelAdmin):
    list_display  = ["trabalhador", "processo", "template", "gerada_em"]
    list_filter   = ["template"]
    readonly_fields = ["gerada_em"]


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ["nome_exibicao", "identificador", "nome_ficheiro_docx", "ativo", "criado_em"]
    prepopulated_fields = {"identificador": ("nome_exibicao",)}