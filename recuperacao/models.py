"""
recuperacao/models.py

Modelos de conversas e mensagens.
"""
from django.db import models


class Conversa(models.Model):
    titulo      = models.CharField(max_length=200, default="Nova conversa")
    criada_em   = models.DateTimeField(auto_now_add=True)
    alterada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering           = ["-alterada_em"]
        verbose_name       = "Conversa"
        verbose_name_plural = "Conversas"

    def __str__(self):
        return f"{self.titulo} ({self.criada_em.strftime('%d/%m/%Y')})"


class Mensagem(models.Model):
    PAPEL_CHOICES = [("user", "Utilizador"), ("assistant", "Assistente")]

    conversa  = models.ForeignKey(Conversa, on_delete=models.CASCADE,
                                  related_name="mensagens")
    papel     = models.CharField(max_length=10, choices=PAPEL_CHOICES)
    texto     = models.TextField()
    fontes    = models.JSONField(default=list)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["criada_em"]
        verbose_name = "Mensagem"

    def __str__(self):
        return f"[{self.papel}] {self.texto[:50]}"