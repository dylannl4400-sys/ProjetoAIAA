"""
ingestao/models.py

Modelos da app de ingestão.
Substituem os ficheiros JSON em acordaos_html/.
"""
from django.db import models


class AcordaoIndexado(models.Model):
    """Registo de cada acórdão indexado no ChromaDB."""
    hash_documento = models.CharField(max_length=64, unique=True, db_index=True)
    processo       = models.CharField(max_length=150, blank=True)
    relator        = models.CharField(max_length=200, blank=True)
    tribunal_id    = models.CharField(max_length=20,  blank=True)
    tribunal_nome  = models.CharField(max_length=200, blank=True)
    data_acordao   = models.CharField(max_length=20,  blank=True)
    descritores    = models.TextField(blank=True)
    url            = models.URLField(max_length=500,  blank=True)
    nome_html      = models.CharField(max_length=200, blank=True)
    nome_txt       = models.CharField(max_length=200, blank=True)
    n_chunks       = models.IntegerField(default=0)
    sumario        = models.TextField(blank=True)
    indexado_em    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering           = ["-indexado_em"]
        verbose_name       = "Acórdão Indexado"
        verbose_name_plural = "Acórdãos Indexados"

    def __str__(self):
        return f"{self.processo} ({self.tribunal_id}) — {self.n_chunks} chunks"