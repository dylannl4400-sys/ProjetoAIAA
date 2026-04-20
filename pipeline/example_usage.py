# """
# Pipeline usage example — shows how to combine any Embedder, Chunker
# and VectorStore independently.
# """

# from chroma_store import ChromaStore
# from fixed_chunker import FixedChunker
# from sentence_transformer_embedder import SentenceTransformerEmbedder
# from structure_aware_chunker import StructureAwareChunker

# # from ollama_embedder import OllamaEmbedder
# # from postgres_store import PostgresStore


# def index_document(text_or_path: str, metadata: dict, store, chunker) -> list[str]:
#     """Chunk a document and store all chunks. Returns the list of assigned IDs."""
#     chunks = chunker.split(text_or_path)
#     ids = []
#     for chunk in chunks:
#         chunk_metadata = {**metadata, **{k: v for k, v in chunk.items() if k != "text"}}
#         ids.append(store.add(chunk["text"], chunk_metadata))
#     return ids


# def main() -> None:

#     # ----- swap any of these three lines independently -----
#     embedder = SentenceTransformerEmbedder("paraphrase-multilingual-MiniLM-L12-v2")
#     # embedder = OllamaEmbedder("nomic-embed-text")

#     chunker  = FixedChunker(chunk_size=25, overlap=5)
#     # chunker  = StructureAwareChunker(max_section_chars=1500, overlap=200)

#     store    = ChromaStore(embedder=embedder)
#     # store    = PostgresStore(embedder=embedder, dsn="postgresql://localhost/aiaa")
#     # -------------------------------------------------------

#     print(f"Embedder : {embedder.model_name}  (dim={embedder.dimension})")
#     print(f"Chunker  : {chunker.__class__.__name__}")
#     print(f"Store    : {store.__class__.__name__}\n")

#     sample_text = (
#         "The defendant was acquitted due to lack of evidence. "
#         "The court ruled that the prosecution failed to present "
#         "sufficient material proof to sustain a conviction beyond "
#         "reasonable doubt. The acquittal is final and cannot be appealed. "
#         "Contract nullity requires proof of intent to deceive. "
#         "A contract is considered null and void when one party deliberately "
#         "misrepresents material facts to induce the other party into signing. "
#         "The burden of proof lies with the claimant."
#     )

#     ids = index_document(
#         sample_text,
#         {"type": "ruling", "court": "Tribunal da Relacao de Lisboa", "year": "2023"},
#         store,
#         chunker,
#     )
#     print(f"Indexed : {len(ids)} chunks  ({store.count()} total in store)\n")

#     results = store.search("acquittal for lack of proof", n=3)
#     print("Search results:")
#     for r in results:
#         print(f"  score={r['score']:.3f}  chunk={r['metadata'].get('chunk_index')}  "
#               f"section={r['metadata'].get('section', 'n/a')}")
#         print(f"  {r['text'][:80]} ...\n")


# if __name__ == "__main__":
#     main()
"""
Pipeline usage example — indexes real PDF files and searches them.

Usage
-----
    # Index all PDFs in a folder and search:
    python example_usage.py

    # Index a single PDF:
    python example_usage.py --pdf path/to/document.pdf

    # Search without re-indexing (reuse existing store):
    python example_usage.py --search-only
"""

import argparse
import os

from chroma_store import ChromaStore
from fixed_chunker import FixedChunker
from pdf_loader import TextLoader
from sentence_transformer_embedder import SentenceTransformerEmbedder

# from ollama_embedder import OllamaEmbedder
# from structure_aware_chunker import StructureAwareChunker
# from postgres_store import PostgresStore


# ---------------------------------------------------------------------------
# PDF metadata — infer document type and area from filename conventions
# ---------------------------------------------------------------------------

def infer_metadata(pdf_path: str) -> dict:
    """
    Build document metadata from the PDF filename and loader.

    For real documents replace this with a proper metadata source
    (database, sidecar JSON, etc.).
    """
    loader   = TextLoader(pdf_path)
    base     = os.path.basename(pdf_path).replace(".pdf", "")
    doc_type = "ruling"      if base.startswith("acordao")    else "legislation"
    area     = "civil"       if "responsabilidade" in base    \
          else "labour"      if any(w in base for w in ["trabalho", "despedimento"]) \
          else "contracts"   if "contrato" in base \
          else "general"

    return {
        **loader.metadata(),          # filename, filepath, num_pages, source
        "type": doc_type,
        "area": area,
    }


# ---------------------------------------------------------------------------
# Index one PDF
# ---------------------------------------------------------------------------

def index_pdf(pdf_path: str, store, chunker) -> list[str]:
    """Load a PDF, chunk it, and store all chunks. Returns assigned IDs."""
    loader   = TextLoader(pdf_path)
    text     = loader.load()
    metadata = infer_metadata(pdf_path)

    if not text.strip():
        print(f"  [SKIP] {os.path.basename(pdf_path)} — no text extracted (scanned PDF?)")
        return []

    chunks = chunker.split(text)
    ids    = []
    for chunk in chunks:
        chunk_metadata = {**metadata, **{k: v for k, v in chunk.items() if k != "text"}}
        ids.append(store.add(chunk["text"], chunk_metadata))

    return ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf",         help="Index a single PDF file")
    parser.add_argument("--pdf-dir",     default="legal_docs", help="Folder with PDFs to index (default: legal_docs)")
    parser.add_argument("--search-only", action="store_true",  help="Skip indexing, reuse existing store")
    parser.add_argument("--query",       default="",           help="Question to search (overrides default list)")
    args = parser.parse_args()

    # ----- swap any of these three lines independently -----
    embedder = SentenceTransformerEmbedder("paraphrase-multilingual-MiniLM-L12-v2")
    chunker  = FixedChunker(chunk_size=250, overlap=50)
    store    = ChromaStore(embedder=embedder, persist_directory="./chroma_db")
    # -------------------------------------------------------

    print(f"Embedder : {embedder.model_name}  (dim={embedder.dimension})")
    print(f"Chunker  : {chunker.__class__.__name__}  "
          f"(chunk_size={chunker.chunk_size}, overlap={chunker.overlap})")
    print(f"Store    : {store.__class__.__name__}\n")

    # ── INDEXATION ──────────────────────────────────────────────────
    if not args.search_only:
        pdfs = []

        if args.pdf:
            pdfs = [args.pdf]
        elif os.path.isdir(args.pdf_dir):
            pdfs = [
                os.path.join(args.pdf_dir, f)
                for f in sorted(os.listdir(args.pdf_dir))
                if f.endswith(".pdf")
            ]
        else:
            print(f"[WARN] Folder '{args.pdf_dir}' not found — using sample text instead.\n")
            _index_sample_text(store, chunker)

        for pdf_path in pdfs:
            print(f"Indexing: {os.path.basename(pdf_path)} ...", end=" ", flush=True)
            ids = index_pdf(pdf_path, store, chunker)
            print(f"{len(ids)} chunks")

        print(f"\nTotal in store: {store.count()} chunks\n")

    else:
        print(f"[search-only]  Store has {store.count()} chunks\n")

    # ── SEARCH ──────────────────────────────────────────────────────
    queries = [args.query] if args.query else [
        "Qual o prazo de prescrição para responsabilidade civil?",
        "Quais os requisitos para anular um contrato?",
        "O que acontece em caso de despedimento ilícito?",
    ]

    for query in queries:
        print(f"Query: {query}")
        print("-" * 60)
        results = store.search(query, n=3)

        if not results:
            print("  (no results)\n")
            continue

        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            print(f"  [{i}] score={r['score']:.3f}  "
                  f"type={meta.get('type','?')}  "
                  f"file={meta.get('filename','?')}  "
                  f"chunk={meta.get('chunk_index','?')}/{meta.get('chunk_total','?')}")
            print(f"       {r['text'][:120].strip()} ...")
        print()


def _index_sample_text(store, chunker) -> None:
    """Fallback: index hardcoded sample text when no PDFs are available."""
    sample = (
        "O réu foi absolvido por falta de prova. "
        "O tribunal entendeu que a acusação não apresentou "
        "prova suficiente para sustentar uma condenação. "
        "A nulidade do contrato requer prova de intenção de enganar. "
        "O prazo de prescrição em litígios laborais é de um ano."
    )
    chunks = chunker.split(sample)
    for chunk in chunks:
        meta = {**{"type": "sample", "filename": "sample_text"}, **{k: v for k, v in chunk.items() if k != "text"}}
        store.add(chunk["text"], meta)
    print(f"Indexed sample text: {len(chunks)} chunks\n")


if __name__ == "__main__":
    main()