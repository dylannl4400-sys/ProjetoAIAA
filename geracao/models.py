"""
geracao/models.py

Modelos da app de geração de peças processuais.
"""
from django.db import models


class Template(models.Model):
    """Template de peça processual com marcadores."""
    identificador       = models.SlugField(max_length=50, unique=True, help_text="ID interno (ex: contestacao)")
    nome_exibicao       = models.CharField(max_length=100, help_text="Nome que aparece na lista")
    nome_ficheiro_docx  = models.CharField(max_length=200, help_text="Nome do ficheiro .docx em pipeline/legal_docs/")
    descricao           = models.TextField(blank=True)
    campos              = models.JSONField(default=list, blank=True, help_text="Marcadores {{...}} detectados no documento")
    ativo               = models.BooleanField(default=True)
    criado_em           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["nome_exibicao"]
        verbose_name = "Template"

    def __str__(self):
        return f"{self.nome_exibicao} ({self.identificador})"


class PecaGerada(models.Model):
    """Registo de cada peça processual gerada."""
    template    = models.ForeignKey(Template, on_delete=models.SET_NULL,
                                    null=True, blank=True)
    processo    = models.CharField(max_length=150, blank=True)
    trabalhador = models.CharField(max_length=200, blank=True)
    gerada_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["-gerada_em"]
        verbose_name = "Peça Gerada"

    def __str__(self):
        return f"{self.template} — {self.trabalhador} ({self.gerada_em.strftime('%d/%m/%Y')})"