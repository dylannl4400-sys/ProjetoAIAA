"""
config.py

Loads config.json and exposes typed dataclasses for every section.
All pipeline components receive their parameters from here — no
magic numbers anywhere else in the codebase.

Usage
-----
    from config import load_config, build_embedder, build_chunker, \
                       build_store, build_prompt_builder, build_llm

    cfg       = load_config()                  # reads config.json
    embedder  = build_embedder(cfg.embedder)
    chunker   = build_chunker(cfg.chunker)
    store     = build_store(cfg.vector_store, embedder)
    builder   = build_prompt_builder(cfg.prompt_builder)
    llm       = build_llm(cfg.llm)

    from retriever import Retriever
    retriever = Retriever(store, builder, llm, cfg.retriever.n_results)
    result    = retriever.ask("Qual o prazo de prescrição em litígios laborais?")

Config path
-----------
    Default: config.json in the same directory as this file.
    Override: load_config("path/to/other_config.json")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Dataclasses — one per config section
# ---------------------------------------------------------------------------

@dataclass
class EmbedderConfig:
    provider:   str   # "sentence_transformer" | "ollama"
    model_name: str
    base_url:   str   = "http://localhost:11434"


@dataclass
class ChunkerConfig:
    strategy:         str   # "fixed" | "structure_aware"
    chunk_size:       int   = 1000
    overlap:          int   = 200
    max_section_chars: int  = 1500


@dataclass
class VectorStoreConfig:
    provider:          str   # "chroma" | "postgres"
    collection_name:   str   = "legal_docs"
    persist_directory: str   = "./chroma_db"
    dsn:               str   = "postgresql://localhost/aiaa"
    table_name:        str   = "legal_docs"


@dataclass
class RetrieverConfig:
    n_results: int          = 5
    filters:   dict | None  = None


@dataclass
class PromptBuilderConfig:
    strategy:   str    # "basic" | "legal"
    max_chunks: int    = 5
    min_score:  float  = 0.3


@dataclass
class LLMConfig:
    provider:    str    # "echo" | "ollama"
    model_name:  str    = "mistral"
    base_url:    str    = "http://localhost:11434"
    temperature: float  = 0.0
    timeout:     int    = 120


@dataclass
class EvalConfig:
    top_n:           int               = 5
    chunk_configs:   list[list[int]]   = field(default_factory=list)
    embedder_models: list[str]         = field(default_factory=list)


@dataclass
class Config:
    embedder:       EmbedderConfig
    chunker:        ChunkerConfig
    vector_store:   VectorStoreConfig
    retriever:      RetrieverConfig
    prompt_builder: PromptBuilderConfig
    llm:            LLMConfig
    eval:           EvalConfig


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str | None = None) -> Config:
    """
    Load and parse config.json into a typed Config object.

    Args:
        path: Path to the JSON config file.
              Defaults to config.json in the same directory as this file.

    Returns:
        Fully populated Config dataclass.

    Raises:
        FileNotFoundError: if the config file does not exist.
        KeyError:          if a required field is missing from the file.
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "config.json")

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    return Config(
        embedder=EmbedderConfig(**raw["embedder"]),
        chunker=ChunkerConfig(**raw["chunker"]),
        vector_store=VectorStoreConfig(**raw["vector_store"]),
        retriever=RetrieverConfig(**raw["retriever"]),
        prompt_builder=PromptBuilderConfig(**raw["prompt_builder"]),
        llm=LLMConfig(**raw["llm"]),
        eval=EvalConfig(**raw["eval"]),
    )


# ---------------------------------------------------------------------------
# Factory functions — build components from config sections
# ---------------------------------------------------------------------------

def build_embedder(cfg: EmbedderConfig):
    """Instantiate the configured Embedder implementation."""
    if cfg.provider == "sentence_transformer":
        from sentence_transformer_embedder import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder(cfg.model_name)

    if cfg.provider == "ollama":
        from ollama_embedder import OllamaEmbedder
        return OllamaEmbedder(cfg.model_name, cfg.base_url)

    raise ValueError(f"Unknown embedder provider: '{cfg.provider}'. "
                     f"Expected 'sentence_transformer' or 'ollama'.")


def build_chunker(cfg: ChunkerConfig):
    """Instantiate the configured Chunker implementation."""
    if cfg.strategy == "fixed":
        from fixed_chunker import FixedChunker
        return FixedChunker(cfg.chunk_size, cfg.overlap)

    if cfg.strategy == "structure_aware":
        from structure_aware_chunker import StructureAwareChunker
        return StructureAwareChunker(cfg.max_section_chars, cfg.overlap)

    raise ValueError(f"Unknown chunker strategy: '{cfg.strategy}'. "
                     f"Expected 'fixed' or 'structure_aware'.")


def build_store(cfg: VectorStoreConfig, embedder):
    """Instantiate the configured VectorStore implementation."""
    if cfg.provider == "chroma":
        from chroma_store import ChromaStore
        return ChromaStore(embedder, cfg.collection_name, cfg.persist_directory)

    if cfg.provider == "postgres":
        from postgres_store import PostgresStore
        return PostgresStore(embedder, cfg.dsn, cfg.table_name)

    raise ValueError(f"Unknown vector_store provider: '{cfg.provider}'. "
                     f"Expected 'chroma' or 'postgres'.")


def build_prompt_builder(cfg: PromptBuilderConfig):
    """Instantiate the configured PromptBuilder implementation."""
    if cfg.strategy == "basic":
        from basic_prompt_builder import BasicPromptBuilder
        return BasicPromptBuilder(cfg.max_chunks)

    if cfg.strategy == "legal":
        from legal_prompt_builder import LegalPromptBuilder
        return LegalPromptBuilder(cfg.max_chunks, cfg.min_score)

    raise ValueError(f"Unknown prompt_builder strategy: '{cfg.strategy}'. "
                     f"Expected 'basic' or 'legal'.")


def build_llm(cfg: LLMConfig):
    """Instantiate the configured LLM implementation."""
    if cfg.provider == "echo":
        from echo_llm import EchoLLM
        return EchoLLM()

    if cfg.provider == "ollama":
        from ollama_llm import OllamaLLM
        return OllamaLLM(cfg.model_name, cfg.base_url, cfg.temperature, cfg.timeout)

    raise ValueError(f"Unknown LLM provider: '{cfg.provider}'. "
                     f"Expected 'echo' or 'ollama'.")