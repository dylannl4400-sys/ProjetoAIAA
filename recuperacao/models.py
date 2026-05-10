# """
# recuperacao/models.py

# Modelos de conversas e mensagens.
# """
# from django.db import models


# class Conversa(models.Model):
#     titulo      = models.CharField(max_length=200, default="Nova conversa")
#     criada_em   = models.DateTimeField(auto_now_add=True)
#     alterada_em = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering           = ["-alterada_em"]
#         verbose_name       = "Conversa"
#         verbose_name_plural = "Conversas"

#     def __str__(self):
#         return f"{self.titulo} ({self.criada_em.strftime('%d/%m/%Y')})"


# class Mensagem(models.Model):
#     PAPEL_CHOICES = [("user", "Utilizador"), ("assistant", "Assistente")]

#     conversa  = models.ForeignKey(Conversa, on_delete=models.CASCADE,
#                                   related_name="mensagens")
#     papel     = models.CharField(max_length=10, choices=PAPEL_CHOICES)
#     texto     = models.TextField()
#     fontes    = models.JSONField(default=list)
#     criada_em = models.DateTimeField(auto_now_add=True)
"""
recuperacao/models.py
"""
from django.db import models


class Utilizador(models.Model):
    """Utilizador simples sem autenticacao Django completa."""
    nome        = models.CharField(max_length=100)
    email       = models.EmailField(unique=True)
    senha_hash  = models.CharField(max_length=256)  # bcrypt hash
    criado_em   = models.DateTimeField(auto_now_add=True)
    ultimo_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering     = ["nome"]
        verbose_name = "Utilizador"

    def __str__(self):
        return f"{self.nome} <{self.email}>"


class Conversa(models.Model):
    utilizador  = models.ForeignKey(
        Utilizador, on_delete=models.CASCADE,
        related_name="conversas", null=True, blank=True
    )
    titulo      = models.CharField(max_length=200, default="Nova conversa")
    criada_em   = models.DateTimeField(auto_now_add=True)
    alterada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-alterada_em"]
        verbose_name        = "Conversa"
        verbose_name_plural = "Conversas"

    def __str__(self):
        return f"{self.titulo} ({self.criada_em.strftime('%d/%m/%Y')})"


class Mensagem(models.Model):
    PAPEL_CHOICES = [("user", "Utilizador"), ("assistant", "Assistente")]

    conversa  = models.ForeignKey(
        Conversa, on_delete=models.CASCADE, related_name="mensagens"
    )
    papel     = models.CharField(max_length=10, choices=PAPEL_CHOICES)
    texto     = models.TextField()
    fontes    = models.JSONField(default=list)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["criada_em"]
        verbose_name = "Mensagem"

    def __str__(self):
        return f"[{self.papel}] {self.texto[:50]}"


class FonteFeedback(models.Model):
    """Registo de feedback (relevância e remoção) de fontes por mensagem."""
    mensagem    = models.ForeignKey(Mensagem, on_delete=models.CASCADE, related_name="feedbacks")
    fonte_id    = models.CharField(max_length=200, help_text="ID da fonte (ex: número do processo)")
    relevancia  = models.IntegerField(default=0, help_text="-1: Down, 0: Neutro, 1: Up")
    removida    = models.BooleanField(default=False)
    comentario  = models.TextField(blank=True, null=True)
    criado_em   = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("mensagem", "fonte_id")
        verbose_name    = "Feedback de Fonte"

    def __str__(self):
        status = "👍" if self.relevancia > 0 else "👎" if self.relevancia < 0 else "Neutral"
        if self.removida: status += " (Removida)"
        return f"Feedback {self.fonte_id} em Msg {self.mensagem_id}: {status}"