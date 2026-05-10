# exportar_chunks.py
from config import load_config, build_embedder, build_store
import json

cfg      = load_config()
embedder = build_embedder(cfg.embedder)
store    = build_store(cfg.vector_store, embedder)

# Pesquisa neutra para trazer todos
total  = store.count()
chunks = store.search("direito jurídico acórdão", n=min(total, 5000))

with open("chunks_exportados.json", "w", encoding="utf-8") as f:
    json.dump([
        {
            "processo": c["metadata"].get("processo", ""),
            "secção":   c["metadata"].get("section", ""),
            "tribunal": c["metadata"].get("court", ""),
            "texto":    c["text"],
            "score":    c["score"],
        }
        for c in chunks
    ], f, ensure_ascii=False, indent=2)

print(f"Exportados {len(chunks)} chunks para chunks_exportados.json")