from django.contrib import admin
from .models import AcordaoIndexado, AcordaoChunk

class AcordaoChunkInline(admin.TabularInline):
    model = AcordaoChunk
    extra = 0
    fields = ("indice", "seccao", "texto_curto")
    readonly_fields = ("indice", "seccao", "texto_curto")
    can_delete = False

    def texto_curto(self, obj):
        return obj.texto[:100] + "..." if len(obj.texto) > 100 else obj.texto
    texto_curto.short_description = "Texto (Início)"

@admin.register(AcordaoIndexado)
class AcordaoIndexadoAdmin(admin.ModelAdmin):
    list_display = ("processo", "tribunal_id", "data_acordao", "n_chunks", "indexado_em")
    search_fields = ("processo", "relator", "descritores")
    list_filter = ("tribunal_id", "indexado_em")
    inlines = [AcordaoChunkInline]

@admin.register(AcordaoChunk)
class AcordaoChunkAdmin(admin.ModelAdmin):
    list_display = ("acordao", "indice", "seccao", "texto_preview")
    list_filter = ("seccao",)
    search_fields = ("texto", "acordao__processo")

    def texto_preview(self, obj):
        return obj.texto[:80] + "..."
    texto_preview.short_description = "Antevisão do Texto"