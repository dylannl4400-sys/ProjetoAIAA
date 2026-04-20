"""
geracao/models.py

Modelos da app de geração de peças processuais.
"""
from django.db import models


class Template(models.Model):
    """Template de peça processual com marcadores."""
    nome        = models.CharField(max_length=100, unique=True)
    descricao   = models.TextField(blank=True)
    ficheiro_js = models.CharField(max_length=200)  # ex: "gerar_carta_cessacao.js"
    ativo       = models.BooleanField(default=True)
    criado_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["nome"]
        verbose_name = "Template"

    def __str__(self):
        return self.nome


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