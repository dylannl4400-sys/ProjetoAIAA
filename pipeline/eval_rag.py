# """
# RAG pipeline evaluator — three dimensions.

# Compares all combinations of:
#     - Embedder       (model used to generate vectors)
#     - chunk_size     (maximum characters per chunk)
#     - overlap        (shared characters between consecutive chunks)

# against a fixed evaluation dataset and reports Hit Rate and MRR
# for every combination, grouped by embedder.

# Metrics
# -------
# Hit Rate @ N  — fraction of questions where the expected chunk appears
#                 in the top-N results. Primary metric.
# MRR @ N       — Mean Reciprocal Rank: rewards finding the correct chunk
#                 at a higher rank (rank 1 = 1.0, rank 5 = 0.2).

# Usage
# -----
#     python eval_rag.py

#     # Run only fast embedders (skip slow ones):
#     python eval_rag.py --fast

# Output
# ------
#     Per-embedder ranked tables + overall best combination.
#     Detailed per-question breakdown for the globally best config.
# """

# import argparse
# import math
# import os
# import shutil
# import textwrap
# from dataclasses import dataclass, field

# from embedder import Embedder
# from fixed_chunker import FixedChunker
# from chroma_store import ChromaStore
# from sentence_transformer_embedder import SentenceTransformerEmbedder


# # ---------------------------------------------------------------------------
# # Evaluation dataset
# # Replace / extend with real legal documents and questions.
# # Aim for 20-30 pairs covering your actual document collection.
# # ---------------------------------------------------------------------------

# DOCUMENTS = [
#     {
#         "text": (
#             "The defendant was acquitted due to lack of evidence. "
#             "The court ruled that the prosecution failed to present "
#             "sufficient material proof to sustain a conviction beyond "
#             "reasonable doubt. The acquittal is final and cannot be appealed."
#         ),
#         "metadata": {"type": "ruling", "court": "Tribunal da Relacao de Lisboa", "year": "2023"},
#     },
#     {
#         "text": (
#             "Contract nullity requires proof of intent to deceive. "
#             "A contract is considered null and void when one party "
#             "deliberately misrepresents material facts to induce the "
#             "other party into signing. The burden of proof lies with "
#             "the claimant."
#         ),
#         "metadata": {"type": "doctrine", "area": "civil", "year": "2022"},
#     },
#     {
#         "text": (
#             "Statute of limitations in labour disputes is one year. "
#             "Claims must be filed within twelve months of the date on "
#             "which the employee became aware of the violation. "
#             "Failure to comply with this deadline results in the claim "
#             "being time-barred."
#         ),
#         "metadata": {"type": "legislation", "area": "labour", "year": "2021"},
#     },
# ]

# EVAL_SET = [
#     {
#         "question": "Was the defendant found guilty or not guilty?",
#         "expected_fragment": "acquitted due to lack of evidence",
#     },
#     {
#         "question": "What is required to prove contract nullity?",
#         "expected_fragment": "intent to deceive",
#     },
#     {
#         "question": "How long does an employee have to file a labour claim?",
#         "expected_fragment": "twelve months",
#     },
#     {
#         "question": "Can the acquittal ruling be challenged in a higher court?",
#         "expected_fragment": "cannot be appealed",
#     },
#     {
#         "question": "Who must prove that a contract was signed under deception?",
#         "expected_fragment": "burden of proof lies with the claimant",
#     },
# ]

# # ---------------------------------------------------------------------------
# # Configurations
# # ---------------------------------------------------------------------------

# # Embedders to evaluate.
# # Add or remove entries freely — each must be an (label, Embedder) tuple.
# # The label is used in the report; keep it short and descriptive.
# EMBEDDERS: list[tuple[str, Embedder]] = [
#     (
#         "MiniLM-multilingual-384",
#         SentenceTransformerEmbedder("paraphrase-multilingual-MiniLM-L12-v2"),
#     ),
#     (
#         "e5-multilingual-base-768",
#         SentenceTransformerEmbedder("intfloat/multilingual-e5-base"),
#     ),
#     # Uncomment to include the heavier model:
#     # (
#     #     "e5-multilingual-large-1024",
#     #     SentenceTransformerEmbedder("intfloat/multilingual-e5-large"),
#     # ),
#     # Uncomment when Ollama is running:
#     # (
#     #     "nomic-embed-text-768",
#     #     OllamaEmbedder("nomic-embed-text"),
#     # ),
# ]

# # Fast-only subset (--fast flag) — skips heavier models
# EMBEDDERS_FAST: list[tuple[str, Embedder]] = [
#     (label, emb) for label, emb in EMBEDDERS
#     if "large" not in label and "nomic" not in label
# ]

# # Chunk configurations to compare: (chunk_size, overlap)
# CHUNK_CONFIGS: list[tuple[int, int]] = [
#     (300,   30),
#     (500,   50),
#     (500,  100),
#     (1000, 100),
#     (1000, 200),
#     (1500, 200),
#     (1500, 300),
# ]

# TOP_N = 5   # evaluate Hit Rate and MRR at top-N results


# # ---------------------------------------------------------------------------
# # Dataclasses
# # ---------------------------------------------------------------------------

# @dataclass
# class QuestionResult:
#     question:          str
#     expected_fragment: str
#     rank:              int | None     # 1-based; None = not found in top-N
#     retrieved_texts:   list[str] = field(default_factory=list)


# @dataclass
# class RunResult:
#     """Result for one (embedder, chunk_size, overlap) combination."""
#     embedder_label: str
#     chunk_size:     int
#     overlap:        int
#     question_results: list[QuestionResult] = field(default_factory=list)

#     @property
#     def hit_rate(self) -> float:
#         hits = sum(1 for r in self.question_results if r.rank is not None)
#         return hits / len(self.question_results) if self.question_results else 0.0

#     @property
#     def mrr(self) -> float:
#         rr = [1 / r.rank if r.rank is not None else 0.0
#               for r in self.question_results]
#         return sum(rr) / len(rr) if rr else 0.0

#     @property
#     def sort_key(self) -> tuple[float, float]:
#         return (self.hit_rate, self.mrr)


# # ---------------------------------------------------------------------------
# # Core evaluation logic
# # ---------------------------------------------------------------------------

# def _build_store(embedder: Embedder, chunk_size: int, overlap: int,
#                  persist_dir: str) -> ChromaStore:
#     """Index all DOCUMENTS with the given embedder and chunk config."""
#     store = ChromaStore(
#         embedder=embedder,
#         collection_name="eval",
#         persist_directory=persist_dir,
#     )
#     chunker = FixedChunker(chunk_size=chunk_size, overlap=overlap)
#     for doc in DOCUMENTS:
#         for chunk in chunker.split(doc["text"]):
#             store.add(chunk["text"], doc["metadata"])
#     return store


# def _find_rank(results: list[dict], expected_fragment: str) -> int | None:
#     """Return the 1-based rank of the first result containing the fragment."""
#     for i, result in enumerate(results, start=1):
#         if expected_fragment.lower() in result["text"].lower():
#             return i
#     return None


# def evaluate_run(
#     embedder_label: str,
#     embedder: Embedder,
#     chunk_size: int,
#     overlap: int,
# ) -> RunResult:
#     """Run a single (embedder, chunk_size, overlap) evaluation."""
#     # Unique directory per combination avoids cross-contamination
#     safe_label = embedder_label.replace("/", "_").replace(" ", "_")
#     persist_dir = f"./eval_chroma_{safe_label}_{chunk_size}_{overlap}"

#     if os.path.exists(persist_dir):
#         shutil.rmtree(persist_dir)

#     store = _build_store(embedder, chunk_size, overlap, persist_dir)
#     run = RunResult(
#         embedder_label=embedder_label,
#         chunk_size=chunk_size,
#         overlap=overlap,
#     )

#     for item in EVAL_SET:
#         results = store.search(item["question"], n=TOP_N)
#         run.question_results.append(
#             QuestionResult(
#                 question=item["question"],
#                 expected_fragment=item["expected_fragment"],
#                 rank=_find_rank(results, item["expected_fragment"]),
#                 retrieved_texts=[r["text"] for r in results],
#             )
#         )

#     shutil.rmtree(persist_dir)
#     return run


# # ---------------------------------------------------------------------------
# # Reporting
# # ---------------------------------------------------------------------------

# def _bar(value: float, width: int = 18) -> str:
#     filled = math.floor(value * width)
#     return "█" * filled + "░" * (width - filled)


# def _marker(i: int) -> str:
#     return " ← best" if i == 0 else ""


# def print_embedder_section(label: str, runs: list[RunResult]) -> None:
#     """Print the ranked chunk-config table for a single embedder."""
#     ranked = sorted(runs, key=lambda r: r.sort_key, reverse=True)
#     dim = EMBEDDERS_FAST[0][1].dimension   # just for display; use actual dim
#     # Find dimension from embedder label
#     for lbl, emb in EMBEDDERS:
#         if lbl == label:
#             dim = emb.dimension
#             break

#     print(f"\n  Embedder : {label}  (dim={dim})")
#     print(f"  {'chunk / overlap':<18} {'Hit Rate':>10}  {'':20} {'MRR':>7}")
#     print(f"  {'-' * 60}")

#     for i, r in enumerate(ranked):
#         print(
#             f"  {r.chunk_size:>4} / {r.overlap:<6}"
#             f"  {r.hit_rate:>8.1%}  {_bar(r.hit_rate)}"
#             f"  {r.mrr:>5.3f}{_marker(i)}"
#         )


# def print_full_report(all_runs: list[RunResult]) -> None:
#     n_embedders = len({r.embedder_label for r in all_runs})
#     n_configs   = len(CHUNK_CONFIGS)
#     n_questions = len(EVAL_SET)

#     print("\n" + "=" * 70)
#     print(f"{'RAG PIPELINE EVALUATION':^70}")
#     print(f"{f'Embedders: {n_embedders}  ·  Chunk configs: {n_configs}  ·  Questions: {n_questions}':^70}")
#     print(f"{'Hit Rate and MRR @ top-' + str(TOP_N):^70}")
#     print("=" * 70)

#     # Per-embedder sections
#     for label, _ in EMBEDDERS:
#         runs = [r for r in all_runs if r.embedder_label == label]
#         if runs:
#             print_embedder_section(label, runs)

#     # Overall best
#     best = max(all_runs, key=lambda r: r.sort_key)
#     print("\n" + "=" * 70)
#     print("  OVERALL BEST COMBINATION")
#     print(f"  Embedder   : {best.embedder_label}")
#     print(f"  chunk_size : {best.chunk_size}")
#     print(f"  overlap    : {best.overlap}")
#     print(f"  Hit Rate   : {best.hit_rate:.1%}   MRR: {best.mrr:.3f}")
#     print("=" * 70)


# def print_detail(run: RunResult) -> None:
#     """Print per-question breakdown for a single run."""
#     print(f"\nDetail — {run.embedder_label}  chunk={run.chunk_size}  overlap={run.overlap}")
#     print("-" * 65)
#     for qr in run.question_results:
#         status = f"rank {qr.rank}" if qr.rank else "NOT FOUND"
#         print(f"  [{status:^10}]  {textwrap.shorten(qr.question, 52)}")


# # ---------------------------------------------------------------------------
# # Entry point
# # ---------------------------------------------------------------------------

# def _parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(description="Evaluate RAG pipeline configurations.")
#     parser.add_argument(
#         "--fast", action="store_true",
#         help="Skip slow/large embedder models."
#     )
#     return parser.parse_args()


# def main() -> None:
#     args = _parse_args()
#     embedders = EMBEDDERS_FAST if args.fast else EMBEDDERS
#     total = len(embedders) * len(CHUNK_CONFIGS)

#     print(f"Evaluating {len(embedders)} embedder(s) × "
#           f"{len(CHUNK_CONFIGS)} chunk configs × "
#           f"{len(EVAL_SET)} questions "
#           f"= {total} runs\n")

#     all_runs: list[RunResult] = []
#     run_count = 0

#     for emb_label, embedder in embedders:
#         print(f"\n── {emb_label} ──")
#         for chunk_size, overlap in CHUNK_CONFIGS:
#             run_count += 1
#             print(
#                 f"  [{run_count:>2}/{total}]  "
#                 f"chunk={chunk_size:>4}  overlap={overlap:>3} … ",
#                 end="", flush=True,
#             )
#             run = evaluate_run(emb_label, embedder, chunk_size, overlap)
#             all_runs.append(run)
#             print(f"hit_rate={run.hit_rate:.1%}  mrr={run.mrr:.3f}")

#     print_full_report(all_runs)

#     best = max(all_runs, key=lambda r: r.sort_key)
#     print_detail(best)


# if __name__ == "__main__":
#     main()

# """
# RAG pipeline evaluator — three dimensions.

# Compares all combinations of:
#     - Embedder       (model used to generate vectors)
#     - chunk_size     (maximum characters per chunk)
#     - overlap        (shared characters between consecutive chunks)

# against a fixed evaluation dataset and reports Hit Rate and MRR
# for every combination, grouped by embedder.

# Metrics
# -------
# Hit Rate @ N  — fraction of questions where the expected chunk appears
#                 in the top-N results. Primary metric.
# MRR @ N       — Mean Reciprocal Rank: rewards finding the correct chunk
#                 at a higher rank (rank 1 = 1.0, rank 5 = 0.2).

# Usage
# -----
#     python eval_rag.py

#     # Run only fast embedders (skip slow ones):
#     python eval_rag.py --fast

# Output
# ------
#     Per-embedder ranked tables + overall best combination.
#     Detailed per-question breakdown for the globally best config.
# """

# import argparse
# import math
# import os
# import shutil
# import textwrap
# from dataclasses import dataclass, field

# from embedder import Embedder
# from fixed_chunker import FixedChunker
# from chroma_store import ChromaStore
# from sentence_transformer_embedder import SentenceTransformerEmbedder


# # ---------------------------------------------------------------------------
# # Evaluation dataset
# # Replace / extend with real legal documents and questions.
# # Aim for 20-30 pairs covering your actual document collection.
# # ---------------------------------------------------------------------------

# DOCUMENTS = [
#     {
#         "text": (
#             "The defendant was acquitted due to lack of evidence. "
#             "The court ruled that the prosecution failed to present "
#             "sufficient material proof to sustain a conviction beyond "
#             "reasonable doubt. The acquittal is final and cannot be appealed."
#         ),
#         "metadata": {"type": "ruling", "court": "Tribunal da Relacao de Lisboa", "year": "2023"},
#     },
#     {
#         "text": (
#             "Contract nullity requires proof of intent to deceive. "
#             "A contract is considered null and void when one party "
#             "deliberately misrepresents material facts to induce the "
#             "other party into signing. The burden of proof lies with "
#             "the claimant."
#         ),
#         "metadata": {"type": "doctrine", "area": "civil", "year": "2022"},
#     },
#     {
#         "text": (
#             "Statute of limitations in labour disputes is one year. "
#             "Claims must be filed within twelve months of the date on "
#             "which the employee became aware of the violation. "
#             "Failure to comply with this deadline results in the claim "
#             "being time-barred."
#         ),
#         "metadata": {"type": "legislation", "area": "labour", "year": "2021"},
#     },
# ]

# EVAL_SET = [
#     {
#         "question": "Was the defendant found guilty or not guilty?",
#         "expected_fragment": "acquitted due to lack of evidence",
#     },
#     {
#         "question": "What is required to prove contract nullity?",
#         "expected_fragment": "intent to deceive",
#     },
#     {
#         "question": "How long does an employee have to file a labour claim?",
#         "expected_fragment": "twelve months",
#     },
#     {
#         "question": "Can the acquittal ruling be challenged in a higher court?",
#         "expected_fragment": "cannot be appealed",
#     },
#     {
#         "question": "Who must prove that a contract was signed under deception?",
#         "expected_fragment": "burden of proof lies with the claimant",
#     },
# ]

# # ---------------------------------------------------------------------------
# # Configurations
# # ---------------------------------------------------------------------------

# # Embedders to evaluate.
# # Add or remove entries freely — each must be an (label, Embedder) tuple.
# # The label is used in the report; keep it short and descriptive.
# EMBEDDERS: list[tuple[str, Embedder]] = [
#     (
#         "MiniLM-multilingual-384",
#         SentenceTransformerEmbedder("paraphrase-multilingual-MiniLM-L12-v2"),
#     ),
#     (
#         "e5-multilingual-base-768",
#         SentenceTransformerEmbedder("intfloat/multilingual-e5-base"),
#     ),
#     # Uncomment to include the heavier model:
#     # (
#     #     "e5-multilingual-large-1024",
#     #     SentenceTransformerEmbedder("intfloat/multilingual-e5-large"),
#     # ),
#     # Uncomment when Ollama is running:
#     # (
#     #     "nomic-embed-text-768",
#     #     OllamaEmbedder("nomic-embed-text"),
#     # ),
# ]

# # Fast-only subset (--fast flag) — skips heavier models
# EMBEDDERS_FAST: list[tuple[str, Embedder]] = [
#     (label, emb) for label, emb in EMBEDDERS
#     if "large" not in label and "nomic" not in label
# ]

# # Chunk configurations to compare: (chunk_size, overlap)
# CHUNK_CONFIGS: list[tuple[int, int]] = [
#     (300,   30),
#     (500,   50),
#     (500,  100),
#     (1000, 100),
#     (1000, 200),
#     (1500, 200),
#     (1500, 300),
# ]

# TOP_N = 5   # evaluate Hit Rate and MRR at top-N results


# # ---------------------------------------------------------------------------
# # Dataclasses
# # ---------------------------------------------------------------------------

# @dataclass
# class QuestionResult:
#     question:          str
#     expected_fragment: str
#     rank:              int | None     # 1-based; None = not found in top-N
#     retrieved_texts:   list[str] = field(default_factory=list)


# @dataclass
# class RunResult:
#     """Result for one (embedder, chunk_size, overlap) combination."""
#     embedder_label: str
#     chunk_size:     int
#     overlap:        int
#     question_results: list[QuestionResult] = field(default_factory=list)

#     @property
#     def hit_rate(self) -> float:
#         hits = sum(1 for r in self.question_results if r.rank is not None)
#         return hits / len(self.question_results) if self.question_results else 0.0

#     @property
#     def mrr(self) -> float:
#         rr = [1 / r.rank if r.rank is not None else 0.0
#               for r in self.question_results]
#         return sum(rr) / len(rr) if rr else 0.0

#     @property
#     def sort_key(self) -> tuple[float, float]:
#         return (self.hit_rate, self.mrr)


# # ---------------------------------------------------------------------------
# # Core evaluation logic
# # ---------------------------------------------------------------------------

# def _build_store(embedder: Embedder, chunk_size: int, overlap: int,
#                  persist_dir: str) -> ChromaStore:
#     """Index all DOCUMENTS with the given embedder and chunk config."""
#     store = ChromaStore(
#         embedder=embedder,
#         collection_name="eval",
#         persist_directory=persist_dir,
#     )
#     chunker = FixedChunker(chunk_size=chunk_size, overlap=overlap)
#     for doc in DOCUMENTS:
#         for chunk in chunker.split(doc["text"]):
#             store.add(chunk["text"], doc["metadata"])
#     return store


# def _find_rank(results: list[dict], expected_fragment: str) -> int | None:
#     """Return the 1-based rank of the first result containing the fragment."""
#     for i, result in enumerate(results, start=1):
#         if expected_fragment.lower() in result["text"].lower():
#             return i
#     return None


# def _close_chroma_and_rmtree(store, persist_dir: str) -> None:
#     """
#     Close a ChromaStore and safely delete its persist directory.

#     ChromaDB maintains an internal singleton (SharedSystemClient) that
#     holds SQLite file handles open even after the ChromaStore instance
#     is closed. On Windows this blocks shutil.rmtree (WinError 32).

#     Fix: call clear_system_cache() to flush the singleton before deletion,
#     then retry up to 5 times with a short delay to let the OS release locks.
#     """
#     import time

#     # Step 1 — close the store instance
#     store.close()

#     # Step 2 — flush ChromaDB's internal singleton handle pool
#     try:
#         import chromadb.api.client as _cc
#         _cc.SharedSystemClient.clear_system_cache()
#     except Exception:
#         pass

#     # Step 3 — retry loop (Windows lock release is not always immediate)
#     for attempt in range(6):
#         try:
#             shutil.rmtree(persist_dir)
#             return
#         except PermissionError:
#             if attempt == 5:
#                 raise
#             time.sleep(0.5)


# def evaluate_run(
#     embedder_label: str,
#     embedder: Embedder,
#     chunk_size: int,
#     overlap: int,
# ) -> RunResult:
#     """Run a single (embedder, chunk_size, overlap) evaluation."""
#     safe_label  = embedder_label.replace("/", "_").replace(" ", "_")
#     persist_dir = f"./eval_chroma_{safe_label}_{chunk_size}_{overlap}"

#     # Clean up any leftover directory from a previous failed run
#     if os.path.exists(persist_dir):
#         shutil.rmtree(persist_dir, ignore_errors=True)

#     store = _build_store(embedder, chunk_size, overlap, persist_dir)
#     run   = RunResult(
#         embedder_label=embedder_label,
#         chunk_size=chunk_size,
#         overlap=overlap,
#     )

#     for item in EVAL_SET:
#         results = store.search(item["question"], n=TOP_N)
#         run.question_results.append(
#             QuestionResult(
#                 question=item["question"],
#                 expected_fragment=item["expected_fragment"],
#                 rank=_find_rank(results, item["expected_fragment"]),
#                 retrieved_texts=[r["text"] for r in results],
#             )
#         )

#     # Close store and delete temp directory — Windows-safe
#     _close_chroma_and_rmtree(store, persist_dir)
#     return run


# # ---------------------------------------------------------------------------
# # Reporting
# # ---------------------------------------------------------------------------

# def _bar(value: float, width: int = 18) -> str:
#     filled = math.floor(value * width)
#     return "█" * filled + "░" * (width - filled)


# def _marker(i: int) -> str:
#     return " ← best" if i == 0 else ""


# def print_embedder_section(label: str, runs: list[RunResult]) -> None:
#     """Print the ranked chunk-config table for a single embedder."""
#     ranked = sorted(runs, key=lambda r: r.sort_key, reverse=True)
#     dim = EMBEDDERS_FAST[0][1].dimension   # just for display; use actual dim
#     # Find dimension from embedder label
#     for lbl, emb in EMBEDDERS:
#         if lbl == label:
#             dim = emb.dimension
#             break

#     print(f"\n  Embedder : {label}  (dim={dim})")
#     print(f"  {'chunk / overlap':<18} {'Hit Rate':>10}  {'':20} {'MRR':>7}")
#     print(f"  {'-' * 60}")

#     for i, r in enumerate(ranked):
#         print(
#             f"  {r.chunk_size:>4} / {r.overlap:<6}"
#             f"  {r.hit_rate:>8.1%}  {_bar(r.hit_rate)}"
#             f"  {r.mrr:>5.3f}{_marker(i)}"
#         )


# def print_full_report(all_runs: list[RunResult]) -> None:
#     n_embedders = len({r.embedder_label for r in all_runs})
#     n_configs   = len(CHUNK_CONFIGS)
#     n_questions = len(EVAL_SET)

#     print("\n" + "=" * 70)
#     print(f"{'RAG PIPELINE EVALUATION':^70}")
#     print(f"{f'Embedders: {n_embedders}  ·  Chunk configs: {n_configs}  ·  Questions: {n_questions}':^70}")
#     print(f"{'Hit Rate and MRR @ top-' + str(TOP_N):^70}")
#     print("=" * 70)

#     # Per-embedder sections
#     for label, _ in EMBEDDERS:
#         runs = [r for r in all_runs if r.embedder_label == label]
#         if runs:
#             print_embedder_section(label, runs)

#     # Overall best
#     best = max(all_runs, key=lambda r: r.sort_key)
#     print("\n" + "=" * 70)
#     print("  OVERALL BEST COMBINATION")
#     print(f"  Embedder   : {best.embedder_label}")
#     print(f"  chunk_size : {best.chunk_size}")
#     print(f"  overlap    : {best.overlap}")
#     print(f"  Hit Rate   : {best.hit_rate:.1%}   MRR: {best.mrr:.3f}")
#     print("=" * 70)


# def print_detail(run: RunResult) -> None:
#     """Print per-question breakdown for a single run."""
#     print(f"\nDetail — {run.embedder_label}  chunk={run.chunk_size}  overlap={run.overlap}")
#     print("-" * 65)
#     for qr in run.question_results:
#         status = f"rank {qr.rank}" if qr.rank else "NOT FOUND"
#         print(f"  [{status:^10}]  {textwrap.shorten(qr.question, 52)}")


# # ---------------------------------------------------------------------------
# # Entry point
# # ---------------------------------------------------------------------------

# def _parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(description="Evaluate RAG pipeline configurations.")
#     parser.add_argument(
#         "--fast", action="store_true",
#         help="Skip slow/large embedder models."
#     )
#     return parser.parse_args()


# def main() -> None:
#     args = _parse_args()
#     embedders = EMBEDDERS_FAST if args.fast else EMBEDDERS
#     total = len(embedders) * len(CHUNK_CONFIGS)

#     print(f"Evaluating {len(embedders)} embedder(s) × "
#           f"{len(CHUNK_CONFIGS)} chunk configs × "
#           f"{len(EVAL_SET)} questions "
#           f"= {total} runs\n")

#     all_runs: list[RunResult] = []
#     run_count = 0

#     for emb_label, embedder in embedders:
#         print(f"\n── {emb_label} ──")
#         for chunk_size, overlap in CHUNK_CONFIGS:
#             run_count += 1
#             print(
#                 f"  [{run_count:>2}/{total}]  "
#                 f"chunk={chunk_size:>4}  overlap={overlap:>3} … ",
#                 end="", flush=True,
#             )
#             run = evaluate_run(emb_label, embedder, chunk_size, overlap)
#             all_runs.append(run)
#             print(f"hit_rate={run.hit_rate:.1%}  mrr={run.mrr:.3f}")

#     print_full_report(all_runs)

#     best = max(all_runs, key=lambda r: r.sort_key)
#     print_detail(best)


# if __name__ == "__main__":
#     main()
# """
# RAG pipeline evaluator — three dimensions.

# Compares all combinations of:
#     - Embedder       (model used to generate vectors)
#     - chunk_size     (maximum characters per chunk)
#     - overlap        (shared characters between consecutive chunks)

# against a fixed evaluation dataset and reports Hit Rate and MRR
# for every combination, grouped by embedder.

# Metrics
# -------
# Hit Rate @ N  — fraction of questions where the expected chunk appears
#                 in the top-N results. Primary metric.
# MRR @ N       — Mean Reciprocal Rank: rewards finding the correct chunk
#                 at a higher rank (rank 1 = 1.0, rank 5 = 0.2).

# Usage
# -----
#     python eval_rag.py

#     # Run only fast embedders (skip slow ones):
#     python eval_rag.py --fast

# Output
# ------
#     Per-embedder ranked tables + overall best combination.
#     Detailed per-question breakdown for the globally best config.
# """

# import argparse
# import math
# import textwrap
# from dataclasses import dataclass, field

# from embedder import Embedder
# from fixed_chunker import FixedChunker
# from chroma_store import ChromaStore
# from sentence_transformer_embedder import SentenceTransformerEmbedder


# # ---------------------------------------------------------------------------
# # Evaluation dataset
# # Replace / extend with real legal documents and questions.
# # Aim for 20-30 pairs covering your actual document collection.
# # ---------------------------------------------------------------------------

# DOCUMENTS = [
#     {
#         "text": (
#             "The defendant was acquitted due to lack of evidence. "
#             "The court ruled that the prosecution failed to present "
#             "sufficient material proof to sustain a conviction beyond "
#             "reasonable doubt. The acquittal is final and cannot be appealed."
#         ),
#         "metadata": {"type": "ruling", "court": "Tribunal da Relacao de Lisboa", "year": "2023"},
#     },
#     {
#         "text": (
#             "Contract nullity requires proof of intent to deceive. "
#             "A contract is considered null and void when one party "
#             "deliberately misrepresents material facts to induce the "
#             "other party into signing. The burden of proof lies with "
#             "the claimant."
#         ),
#         "metadata": {"type": "doctrine", "area": "civil", "year": "2022"},
#     },
#     {
#         "text": (
#             "Statute of limitations in labour disputes is one year. "
#             "Claims must be filed within twelve months of the date on "
#             "which the employee became aware of the violation. "
#             "Failure to comply with this deadline results in the claim "
#             "being time-barred."
#         ),
#         "metadata": {"type": "legislation", "area": "labour", "year": "2021"},
#     },
# ]

# EVAL_SET = [
#     {
#         "question": "Was the defendant found guilty or not guilty?",
#         "expected_fragment": "acquitted due to lack of evidence",
#     },
#     {
#         "question": "What is required to prove contract nullity?",
#         "expected_fragment": "intent to deceive",
#     },
#     {
#         "question": "How long does an employee have to file a labour claim?",
#         "expected_fragment": "twelve months",
#     },
#     {
#         "question": "Can the acquittal ruling be challenged in a higher court?",
#         "expected_fragment": "cannot be appealed",
#     },
#     {
#         "question": "Who must prove that a contract was signed under deception?",
#         "expected_fragment": "burden of proof lies with the claimant",
#     },
# ]

# # ---------------------------------------------------------------------------
# # Configurations
# # ---------------------------------------------------------------------------

# # Embedders to evaluate.
# # Add or remove entries freely — each must be an (label, Embedder) tuple.
# # The label is used in the report; keep it short and descriptive.
# EMBEDDERS: list[tuple[str, Embedder]] = [
#     (
#         "MiniLM-multilingual-384",
#         SentenceTransformerEmbedder("paraphrase-multilingual-MiniLM-L12-v2"),
#     ),
#     (
#         "e5-multilingual-base-768",
#         SentenceTransformerEmbedder("intfloat/multilingual-e5-base"),
#     ),
#     # Uncomment to include the heavier model:
#     # (
#     #     "e5-multilingual-large-1024",
#     #     SentenceTransformerEmbedder("intfloat/multilingual-e5-large"),
#     # ),
#     # Uncomment when Ollama is running:
#     # (
#     #     "nomic-embed-text-768",
#     #     OllamaEmbedder("nomic-embed-text"),
#     # ),
# ]

# # Fast-only subset (--fast flag) — skips heavier models
# EMBEDDERS_FAST: list[tuple[str, Embedder]] = [
#     (label, emb) for label, emb in EMBEDDERS
#     if "large" not in label and "nomic" not in label
# ]

# # Chunk configurations to compare: (chunk_size, overlap)
# CHUNK_CONFIGS: list[tuple[int, int]] = [
#     (300,   30),
#     (500,   50),
#     (500,  100),
#     (1000, 100),
#     (1000, 200),
#     (1500, 200),
#     (1500, 300),
# ]

# TOP_N = 5   # evaluate Hit Rate and MRR at top-N results


# # ---------------------------------------------------------------------------
# # Dataclasses
# # ---------------------------------------------------------------------------

# @dataclass
# class QuestionResult:
#     question:          str
#     expected_fragment: str
#     rank:              int | None     # 1-based; None = not found in top-N
#     retrieved_texts:   list[str] = field(default_factory=list)


# @dataclass
# class RunResult:
#     """Result for one (embedder, chunk_size, overlap) combination."""
#     embedder_label: str
#     chunk_size:     int
#     overlap:        int
#     question_results: list[QuestionResult] = field(default_factory=list)

#     @property
#     def hit_rate(self) -> float:
#         hits = sum(1 for r in self.question_results if r.rank is not None)
#         return hits / len(self.question_results) if self.question_results else 0.0

#     @property
#     def mrr(self) -> float:
#         rr = [1 / r.rank if r.rank is not None else 0.0
#               for r in self.question_results]
#         return sum(rr) / len(rr) if rr else 0.0

#     @property
#     def sort_key(self) -> tuple[float, float]:
#         return (self.hit_rate, self.mrr)


# # ---------------------------------------------------------------------------
# # Core evaluation logic
# # ---------------------------------------------------------------------------

# # ---------------------------------------------------------------------------
# # Core evaluation logic
# # ---------------------------------------------------------------------------

# def _build_store(embedder: Embedder, chunk_size: int, overlap: int) -> ChromaStore:
#     """
#     Index all DOCUMENTS in an in-memory ChromaDB store.

#     Uses EphemeralClient (no disk persistence) so there are no temp
#     directories to manage and no file-lock issues on Windows.
#     """
#     store = ChromaStore(
#         embedder=embedder,
#         collection_name="eval",
#         ephemeral=True,           # in-memory only — no files on disk
#     )
#     chunker = FixedChunker(chunk_size=chunk_size, overlap=overlap)
#     for doc in DOCUMENTS:
#         for chunk in chunker.split(doc["text"]):
#             store.add(chunk["text"], doc["metadata"])
#     return store


# def _find_rank(results: list[dict], expected_fragment: str) -> int | None:
#     """Return the 1-based rank of the first result containing the fragment."""
#     for i, result in enumerate(results, start=1):
#         if expected_fragment.lower() in result["text"].lower():
#             return i
#     return None


# def evaluate_run(
#     embedder_label: str,
#     embedder: Embedder,
#     chunk_size: int,
#     overlap: int,
# ) -> RunResult:
#     """Run a single (embedder, chunk_size, overlap) evaluation."""
#     store = _build_store(embedder, chunk_size, overlap)
#     run   = RunResult(
#         embedder_label=embedder_label,
#         chunk_size=chunk_size,
#         overlap=overlap,
#     )

#     for item in EVAL_SET:
#         results = store.search(item["question"], n=TOP_N)
#         run.question_results.append(
#             QuestionResult(
#                 question=item["question"],
#                 expected_fragment=item["expected_fragment"],
#                 rank=_find_rank(results, item["expected_fragment"]),
#                 retrieved_texts=[r["text"] for r in results],
#             )
#         )

#     # No cleanup needed — EphemeralClient holds everything in memory
#     return run


# # ---------------------------------------------------------------------------
# # Reporting
# # ---------------------------------------------------------------------------

# def _bar(value: float, width: int = 18) -> str:
#     filled = math.floor(value * width)
#     return "█" * filled + "░" * (width - filled)


# def _marker(i: int) -> str:
#     return " ← best" if i == 0 else ""


# def print_embedder_section(label: str, runs: list[RunResult]) -> None:
#     """Print the ranked chunk-config table for a single embedder."""
#     ranked = sorted(runs, key=lambda r: r.sort_key, reverse=True)
#     dim = EMBEDDERS_FAST[0][1].dimension   # just for display; use actual dim
#     # Find dimension from embedder label
#     for lbl, emb in EMBEDDERS:
#         if lbl == label:
#             dim = emb.dimension
#             break

#     print(f"\n  Embedder : {label}  (dim={dim})")
#     print(f"  {'chunk / overlap':<18} {'Hit Rate':>10}  {'':20} {'MRR':>7}")
#     print(f"  {'-' * 60}")

#     for i, r in enumerate(ranked):
#         print(
#             f"  {r.chunk_size:>4} / {r.overlap:<6}"
#             f"  {r.hit_rate:>8.1%}  {_bar(r.hit_rate)}"
#             f"  {r.mrr:>5.3f}{_marker(i)}"
#         )


# def print_full_report(all_runs: list[RunResult]) -> None:
#     n_embedders = len({r.embedder_label for r in all_runs})
#     n_configs   = len(CHUNK_CONFIGS)
#     n_questions = len(EVAL_SET)

#     print("\n" + "=" * 70)
#     print(f"{'RAG PIPELINE EVALUATION':^70}")
#     print(f"{f'Embedders: {n_embedders}  ·  Chunk configs: {n_configs}  ·  Questions: {n_questions}':^70}")
#     print(f"{'Hit Rate and MRR @ top-' + str(TOP_N):^70}")
#     print("=" * 70)

#     # Per-embedder sections
#     for label, _ in EMBEDDERS:
#         runs = [r for r in all_runs if r.embedder_label == label]
#         if runs:
#             print_embedder_section(label, runs)

#     # Overall best
#     best = max(all_runs, key=lambda r: r.sort_key)
#     print("\n" + "=" * 70)
#     print("  OVERALL BEST COMBINATION")
#     print(f"  Embedder   : {best.embedder_label}")
#     print(f"  chunk_size : {best.chunk_size}")
#     print(f"  overlap    : {best.overlap}")
#     print(f"  Hit Rate   : {best.hit_rate:.1%}   MRR: {best.mrr:.3f}")
#     print("=" * 70)


# def print_detail(run: RunResult) -> None:
#     """Print per-question breakdown for a single run."""
#     print(f"\nDetail — {run.embedder_label}  chunk={run.chunk_size}  overlap={run.overlap}")
#     print("-" * 65)
#     for qr in run.question_results:
#         status = f"rank {qr.rank}" if qr.rank else "NOT FOUND"
#         print(f"  [{status:^10}]  {textwrap.shorten(qr.question, 52)}")


# # ---------------------------------------------------------------------------
# # Entry point
# # ---------------------------------------------------------------------------

# def _parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(description="Evaluate RAG pipeline configurations.")
#     parser.add_argument(
#         "--fast", action="store_true",
#         help="Skip slow/large embedder models."
#     )
#     return parser.parse_args()


# def main() -> None:
#     args = _parse_args()
#     embedders = EMBEDDERS_FAST if args.fast else EMBEDDERS
#     total = len(embedders) * len(CHUNK_CONFIGS)

#     print(f"Evaluating {len(embedders)} embedder(s) × "
#           f"{len(CHUNK_CONFIGS)} chunk configs × "
#           f"{len(EVAL_SET)} questions "
#           f"= {total} runs\n")

#     all_runs: list[RunResult] = []
#     run_count = 0

#     for emb_label, embedder in embedders:
#         print(f"\n── {emb_label} ──")
#         for chunk_size, overlap in CHUNK_CONFIGS:
#             run_count += 1
#             print(
#                 f"  [{run_count:>2}/{total}]  "
#                 f"chunk={chunk_size:>4}  overlap={overlap:>3} … ",
#                 end="", flush=True,
#             )
#             run = evaluate_run(emb_label, embedder, chunk_size, overlap)
#             all_runs.append(run)
#             print(f"hit_rate={run.hit_rate:.1%}  mrr={run.mrr:.3f}")

#     print_full_report(all_runs)

#     best = max(all_runs, key=lambda r: r.sort_key)
#     print_detail(best)


# if __name__ == "__main__":
#     main()
"""
RAG pipeline evaluator — three dimensions.

Compares all combinations of:
    - Embedder       (model used to generate vectors)
    - chunk_size     (maximum characters per chunk)
    - overlap        (shared characters between consecutive chunks)

against a fixed evaluation dataset and reports Hit Rate and MRR
for every combination, grouped by embedder.

Metrics
-------
Hit Rate @ N  — fraction of questions where the expected chunk appears
                in the top-N results. Primary metric.
MRR @ N       — Mean Reciprocal Rank: rewards finding the correct chunk
                at a higher rank (rank 1 = 1.0, rank 5 = 0.2).

Usage
-----
    python eval_rag.py

    # Run only fast embedders (skip slow ones):
    python eval_rag.py --fast

Output
------
    Per-embedder ranked tables + overall best combination.
    Detailed per-question breakdown for the globally best config.
"""

import argparse
import math
import textwrap
from dataclasses import dataclass, field

from embedder import Embedder
from fixed_chunker import FixedChunker
from chroma_store import ChromaStore
from sentence_transformer_embedder import SentenceTransformerEmbedder


# ---------------------------------------------------------------------------
# Evaluation dataset
# Replace / extend with real legal documents and questions.
# Aim for 20-30 pairs covering your actual document collection.
# ---------------------------------------------------------------------------

DOCUMENTS = [
    {
        "text": (
            "The defendant was acquitted due to lack of evidence. "
            "The court ruled that the prosecution failed to present "
            "sufficient material proof to sustain a conviction beyond "
            "reasonable doubt. The acquittal is final and cannot be appealed."
        ),
        "metadata": {"type": "ruling", "court": "Tribunal da Relacao de Lisboa", "year": "2023"},
    },
    {
        "text": (
            "Contract nullity requires proof of intent to deceive. "
            "A contract is considered null and void when one party "
            "deliberately misrepresents material facts to induce the "
            "other party into signing. The burden of proof lies with "
            "the claimant."
        ),
        "metadata": {"type": "doctrine", "area": "civil", "year": "2022"},
    },
    {
        "text": (
            "Statute of limitations in labour disputes is one year. "
            "Claims must be filed within twelve months of the date on "
            "which the employee became aware of the violation. "
            "Failure to comply with this deadline results in the claim "
            "being time-barred."
        ),
        "metadata": {"type": "legislation", "area": "labour", "year": "2021"},
    },
]

EVAL_SET = [
    {
        "question": "Was the defendant found guilty or not guilty?",
        "expected_fragment": "acquitted due to lack of evidence",
    },
    {
        "question": "What is required to prove contract nullity?",
        "expected_fragment": "intent to deceive",
    },
    {
        "question": "How long does an employee have to file a labour claim?",
        "expected_fragment": "twelve months",
    },
    {
        "question": "Can the acquittal ruling be challenged in a higher court?",
        "expected_fragment": "cannot be appealed",
    },
    {
        "question": "Who must prove that a contract was signed under deception?",
        "expected_fragment": "burden of proof lies with the claimant",
    },
]

# ---------------------------------------------------------------------------
# Configurations
# ---------------------------------------------------------------------------

# Embedders to evaluate.
# Add or remove entries freely — each must be an (label, Embedder) tuple.
# The label is used in the report; keep it short and descriptive.
EMBEDDERS: list[tuple[str, Embedder]] = [
    (
        "MiniLM-multilingual-384",
        SentenceTransformerEmbedder("paraphrase-multilingual-MiniLM-L12-v2"),
    ),
    (
        "e5-multilingual-base-768",
        SentenceTransformerEmbedder("intfloat/multilingual-e5-base"),
    ),
    # Uncomment to include the heavier model:
    # (
    #     "e5-multilingual-large-1024",
    #     SentenceTransformerEmbedder("intfloat/multilingual-e5-large"),
    # ),
    # Uncomment when Ollama is running:
    # (
    #     "nomic-embed-text-768",
    #     OllamaEmbedder("nomic-embed-text"),
    # ),
]

# Fast-only subset (--fast flag) — skips heavier models
EMBEDDERS_FAST: list[tuple[str, Embedder]] = [
    (label, emb) for label, emb in EMBEDDERS
    if "large" not in label and "nomic" not in label
]

# Chunk configurations to compare: (chunk_size, overlap)
CHUNK_CONFIGS: list[tuple[int, int]] = [
    (300,   30),
    (500,   50),
    (500,  100),
    (1000, 100),
    (1000, 200),
    (1500, 200),
    (1500, 300),
]

TOP_N = 5   # evaluate Hit Rate and MRR at top-N results


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class QuestionResult:
    question:          str
    expected_fragment: str
    rank:              int | None     # 1-based; None = not found in top-N
    retrieved_texts:   list[str] = field(default_factory=list)


@dataclass
class RunResult:
    """Result for one (embedder, chunk_size, overlap) combination."""
    embedder_label: str
    chunk_size:     int
    overlap:        int
    question_results: list[QuestionResult] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        hits = sum(1 for r in self.question_results if r.rank is not None)
        return hits / len(self.question_results) if self.question_results else 0.0

    @property
    def mrr(self) -> float:
        rr = [1 / r.rank if r.rank is not None else 0.0
              for r in self.question_results]
        return sum(rr) / len(rr) if rr else 0.0

    @property
    def sort_key(self) -> tuple[float, float]:
        return (self.hit_rate, self.mrr)


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

def _build_store(embedder: Embedder, chunk_size: int, overlap: int,
                 collection_name: str) -> ChromaStore:
    """
    Index all DOCUMENTS in an in-memory ChromaDB store.

    Uses EphemeralClient (no disk persistence) so there are no temp
    directories to manage and no file-lock issues on Windows.

    Each run uses a unique collection_name to avoid dimension conflicts
    when switching between embedders (e.g. 384-dim vs 768-dim).
    """
    store = ChromaStore(
        embedder=embedder,
        collection_name=collection_name,
        ephemeral=True,
    )
    chunker = FixedChunker(chunk_size=chunk_size, overlap=overlap)
    for doc in DOCUMENTS:
        for chunk in chunker.split(doc["text"]):
            store.add(chunk["text"], doc["metadata"])
    return store


def _find_rank(results: list[dict], expected_fragment: str) -> int | None:
    """Return the 1-based rank of the first result containing the fragment."""
    for i, result in enumerate(results, start=1):
        if expected_fragment.lower() in result["text"].lower():
            return i
    return None


def evaluate_run(
    embedder_label: str,
    embedder: Embedder,
    chunk_size: int,
    overlap: int,
) -> RunResult:
    """Run a single (embedder, chunk_size, overlap) evaluation."""
    # Unique collection name per run — prevents ChromaDB from rejecting
    # a different embedding dimension on a previously created collection.
    safe_label      = embedder_label.replace("/", "_").replace(" ", "_")
    collection_name = f"eval_{safe_label}_{chunk_size}_{overlap}"

    store = _build_store(embedder, chunk_size, overlap, collection_name)
    run   = RunResult(
        embedder_label=embedder_label,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    for item in EVAL_SET:
        results = store.search(item["question"], n=TOP_N)
        run.question_results.append(
            QuestionResult(
                question=item["question"],
                expected_fragment=item["expected_fragment"],
                rank=_find_rank(results, item["expected_fragment"]),
                retrieved_texts=[r["text"] for r in results],
            )
        )

    # No cleanup needed — EphemeralClient holds everything in memory
    return run


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 18) -> str:
    filled = math.floor(value * width)
    return "█" * filled + "░" * (width - filled)


def _marker(i: int) -> str:
    return " ← best" if i == 0 else ""


def print_embedder_section(label: str, runs: list[RunResult]) -> None:
    """Print the ranked chunk-config table for a single embedder."""
    ranked = sorted(runs, key=lambda r: r.sort_key, reverse=True)
    dim = EMBEDDERS_FAST[0][1].dimension   # just for display; use actual dim
    # Find dimension from embedder label
    for lbl, emb in EMBEDDERS:
        if lbl == label:
            dim = emb.dimension
            break

    print(f"\n  Embedder : {label}  (dim={dim})")
    print(f"  {'chunk / overlap':<18} {'Hit Rate':>10}  {'':20} {'MRR':>7}")
    print(f"  {'-' * 60}")

    for i, r in enumerate(ranked):
        print(
            f"  {r.chunk_size:>4} / {r.overlap:<6}"
            f"  {r.hit_rate:>8.1%}  {_bar(r.hit_rate)}"
            f"  {r.mrr:>5.3f}{_marker(i)}"
        )


def print_full_report(all_runs: list[RunResult]) -> None:
    n_embedders = len({r.embedder_label for r in all_runs})
    n_configs   = len(CHUNK_CONFIGS)
    n_questions = len(EVAL_SET)

    print("\n" + "=" * 70)
    print(f"{'RAG PIPELINE EVALUATION':^70}")
    print(f"{f'Embedders: {n_embedders}  ·  Chunk configs: {n_configs}  ·  Questions: {n_questions}':^70}")
    print(f"{'Hit Rate and MRR @ top-' + str(TOP_N):^70}")
    print("=" * 70)

    # Per-embedder sections
    for label, _ in EMBEDDERS:
        runs = [r for r in all_runs if r.embedder_label == label]
        if runs:
            print_embedder_section(label, runs)

    # Overall best
    best = max(all_runs, key=lambda r: r.sort_key)
    print("\n" + "=" * 70)
    print("  OVERALL BEST COMBINATION")
    print(f"  Embedder   : {best.embedder_label}")
    print(f"  chunk_size : {best.chunk_size}")
    print(f"  overlap    : {best.overlap}")
    print(f"  Hit Rate   : {best.hit_rate:.1%}   MRR: {best.mrr:.3f}")
    print("=" * 70)


def print_detail(run: RunResult) -> None:
    """Print per-question breakdown for a single run."""
    print(f"\nDetail — {run.embedder_label}  chunk={run.chunk_size}  overlap={run.overlap}")
    print("-" * 65)
    for qr in run.question_results:
        status = f"rank {qr.rank}" if qr.rank else "NOT FOUND"
        print(f"  [{status:^10}]  {textwrap.shorten(qr.question, 52)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline configurations.")
    parser.add_argument(
        "--fast", action="store_true",
        help="Skip slow/large embedder models."
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    embedders = EMBEDDERS_FAST if args.fast else EMBEDDERS
    total = len(embedders) * len(CHUNK_CONFIGS)

    print(f"Evaluating {len(embedders)} embedder(s) × "
          f"{len(CHUNK_CONFIGS)} chunk configs × "
          f"{len(EVAL_SET)} questions "
          f"= {total} runs\n")

    all_runs: list[RunResult] = []
    run_count = 0

    for emb_label, embedder in embedders:
        print(f"\n── {emb_label} ──")
        for chunk_size, overlap in CHUNK_CONFIGS:
            run_count += 1
            print(
                f"  [{run_count:>2}/{total}]  "
                f"chunk={chunk_size:>4}  overlap={overlap:>3} … ",
                end="", flush=True,
            )
            run = evaluate_run(emb_label, embedder, chunk_size, overlap)
            all_runs.append(run)
            print(f"hit_rate={run.hit_rate:.1%}  mrr={run.mrr:.3f}")

    print_full_report(all_runs)

    best = max(all_runs, key=lambda r: r.sort_key)
    print_detail(best)


if __name__ == "__main__":
    main()