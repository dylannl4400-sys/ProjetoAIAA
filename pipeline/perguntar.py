"""
perguntar.py

Query pipeline — runs after indexar.py has populated the store.

    pergunta → Embedder → VectorStore.search → PromptBuilder → LLM → resposta

All parameters are read from config.json.
The embedder model_name MUST match the one used in indexar.py.

Usage
-----
    # Interactive mode (default)
    python perguntar.py

    # Single question
    python perguntar.py --pergunta "Qual o prazo de prescrição em litígios laborais?"

Prerequisites
-------------
    1. indexar.py must have been run at least once.
    2. Ollama must be running with the configured model pulled:
           ollama pull mistral
           ollama serve          (starts automatically on most systems)
       To test without Ollama, set llm.provider = "echo" in config.json.
"""

import argparse

from config import load_config, build_embedder, build_store, \
                   build_prompt_builder, build_llm
from retriever import Retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_result(result, show_prompt: bool = False) -> None:
    print("\n" + "=" * 65)
    print("RESPOSTA")
    print("=" * 65)
    print(result.answer)

    print("\n" + "-" * 65)
    print(f"FONTES USADAS  ({len(result.sources)} chunks recuperados)")
    print("-" * 65)
    for i, src in enumerate(result.sources, 1):
        meta = src["metadata"]
        filename  = meta.get("filename",  "desconhecido")
        doc_type  = meta.get("type",      "")
        year      = meta.get("year",      "")
        page      = meta.get("page_start", "?")
        section   = meta.get("section",   "")
        score     = src["score"]

        parts = [f"[{i}]", f"score={score:.2f}", filename]
        if doc_type: parts.append(doc_type)
        if year:     parts.append(year)
        if page:     parts.append(f"pág. {page}")
        if section:  parts.append(f"§ {section}")
        print("  " + "  |  ".join(parts))

    if show_prompt:
        print("\n" + "-" * 65)
        print("PROMPT ENVIADO AO LLM")
        print("-" * 65)
        print(result.prompt)

    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# Pipeline setup
# ---------------------------------------------------------------------------

def build_retriever(cfg):
    embedder = build_embedder(cfg.embedder)
    store    = build_store(cfg.vector_store, embedder)
    builder  = build_prompt_builder(cfg.prompt_builder)
    llm      = build_llm(cfg.llm)

    if store.count() == 0:
        print("AVISO: o store está vazio. Corre primeiro: python indexar.py\n")

    return Retriever(
        store=store,
        prompt_builder=builder,
        llm=llm,
        n_results=cfg.retriever.n_results,
        filters=cfg.retriever.filters,
    )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def modo_unico(pergunta: str, show_prompt: bool = False) -> None:
    """Answer a single question and exit."""
    cfg       = load_config()
    retriever = build_retriever(cfg)

    print(f"\nPergunta : {pergunta}")
    result = retriever.ask(pergunta)
    _print_result(result, show_prompt)


def modo_interativo(show_prompt: bool = False) -> None:
    """Interactive REPL — ask multiple questions until 'sair'."""
    cfg       = load_config()
    retriever = build_retriever(cfg)

    print("\nAIAA — Assistente Jurídico")
    print(f"Modelo   : {cfg.llm.model_name}")
    print(f"Embedder : {cfg.embedder.model_name}")
    print("Escreve 'sair' para terminar.\n")

    while True:
        try:
            pergunta = input("Pergunta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nA terminar.")
            break

        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit"}:
            print("A terminar.")
            break

        result = retriever.ask(pergunta)
        _print_result(result, show_prompt)


def main() -> None:
    parser = argparse.ArgumentParser(description="AIAA — Query pipeline")
    parser.add_argument(
        "--pergunta", "-p",
        type=str,
        default=None,
        help="Single question to answer (omit for interactive mode).",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Also print the full prompt sent to the LLM.",
    )
    args = parser.parse_args()

    if args.pergunta:
        modo_unico(args.pergunta, args.prompt)
    else:
        modo_interativo(args.prompt)


if __name__ == "__main__":
    main()
