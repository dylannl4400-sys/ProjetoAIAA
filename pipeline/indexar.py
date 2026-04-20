"""
indexar.py

Indexation pipeline — runs once (or whenever new documents arrive).

    PDF → TextLoader → text → FixedChunker → chunks → Embedder → ChromaStore

All parameters are read from config.json.
Chunks are persisted to disk (./chroma_db) and survive across runs.
Do NOT change the embedder model_name after indexing — re-indexing
all documents would be required.

Usage
-----
    python indexar.py

Add documents to the DOCUMENTOS list below before running.
"""

from config import load_config, build_embedder, build_chunker, build_store
from pdf_loader import TextLoader


# ---------------------------------------------------------------------------
# Documents to index
# Add one entry per PDF. metadata keys are stored with every chunk and
# are available as filters in the retriever (e.g. filter by type or year).
# ---------------------------------------------------------------------------

DOCUMENTOS = [
    {
        "path":     "legal_docs/acordao_01_responsabilidade_civil.pdf",
        "metadata": {"type": "ruling", "court": "Tribunal da Relação de Lisboa", "year": "2024"}
    },
    {
        "path":     "legal_docs/acordao_02_despedimento_ilicito.pdf",
        "metadata": {"type": "ruling", "court": "Tribunal da Relação de Lisboa", "year": "2024"}
    },
    {
        "path":     "legal_docs/acordao_03_anulacao_contrato.pdf",
        "metadata": {"type": "ruling", "court": "Tribunal da Relação de Lisboa", "year": "2024"}
    },
    {
        "path":     "legal_docs/legislacao_01_codigo_civil_responsabilidade.pdf",
        "metadata": {"type": "legislation", "area": "civil", "year": "2023"}
    },
    {
        "path":     "legal_docs/legislacao_02_codigo_trabalho_cessacao.pdf",
        "metadata": {"type": "legislation", "area": "labour", "year": "2023"}
    },
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    if not DOCUMENTOS:
        print("Nenhum documento na lista DOCUMENTOS — adiciona entradas e volta a correr.")
        return

    cfg      = load_config()
    embedder = build_embedder(cfg.embedder)
    chunker  = build_chunker(cfg.chunker)
    store    = build_store(cfg.vector_store, embedder)

    print(f"Embedder  : {embedder.model_name}  (dim={embedder.dimension})")
    print(f"Chunker   : {chunker.__class__.__name__}  "
          f"chunk_size={cfg.chunker.chunk_size}  overlap={cfg.chunker.overlap}")
    print(f"Store     : {store.__class__.__name__}  "
          f"collection={cfg.vector_store.collection_name}\n")

    total_chunks = 0

    for doc in DOCUMENTOS:
        path = doc["path"]
        print(f"A indexar : {path}")

        loader = TextLoader(path)
        texto  = loader.load()

        if not texto.strip():
            print(f"  AVISO: ficheiro vazio ou sem texto extraível — ignorado.\n")
            continue

        # Merge file metadata (filename, num_pages) with user-supplied metadata
        meta   = {**loader.metadata(), **doc["metadata"]}
        chunks = chunker.split(texto)
        
        # StructureAwareChunker accepts PDF path directly to use pdfplumber
        # for section detection via font size / boldness.
        # FixedChunker only accepts plain text.
        from structure_aware_chunker import StructureAwareChunker
        if isinstance(chunker, StructureAwareChunker):
            chunks = chunker.split(path)   # PDF path — preserves typography
        else:
            chunks = chunker.split(texto)  # plain text

        for chunk in chunks:
            chunk_meta = {**meta, **{k: v for k, v in chunk.items() if k != "text"}}
            store.add(chunk["text"], chunk_meta)

        total_chunks += len(chunks)
        print(f"  {len(chunks)} chunks  |  {meta['num_pages']} páginas  |  "
              f"{len(texto)} caracteres\n")

    print(f"Indexação concluída.")
    print(f"  Documentos processados : {len(DOCUMENTOS)}")
    print(f"  Chunks adicionados     : {total_chunks}")
    print(f"  Total no store         : {store.count()} chunks")
    print(f"\nPodes agora correr: python perguntar.py")


if __name__ == "__main__":
    main()
