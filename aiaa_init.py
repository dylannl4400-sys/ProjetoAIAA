"""
aiaa_init.py  —  inicializacao lazy partilhada entre as 3 apps

Os componentes pesados so sao inicializados na primeira chamada,
nao quando o Django carrega os URLs.

Uso em qualquer view:
    from aiaa_init import get_cfg, get_store, get_retriever, get_itij, ITIJ_TRIBUNAIS
"""

import sys
from pathlib import Path

# Garantir que pipeline/ esta no path
_BASE     = Path(__file__).resolve().parent
_PIPELINE = _BASE / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

# ITIJ_TRIBUNAIS e so um dict — importar sem inicializar LLM
try:
    from itij_scraper import ITIJ_TRIBUNAIS
except ImportError:
    ITIJ_TRIBUNAIS = {}

# ---------------------------------------------------------------------------
# Singletons lazy
# ---------------------------------------------------------------------------

_instances = {}


def _init():
    """Inicializa todos os componentes uma unica vez."""
    if _instances:
        return

    from config import (
        load_config, build_embedder, build_store,
        build_prompt_builder, build_llm, build_chunker,
    )
    from retriever          import Retriever
    from document_generator import DocumentGenerator
    from itij_scraper       import ITIJScraper

    cfg       = load_config()
    embedder  = build_embedder(cfg.embedder)
    store     = build_store(cfg.vector_store, embedder)
    builder   = build_prompt_builder(cfg.prompt_builder)
    llm       = build_llm(cfg.llm)
    chunker   = build_chunker(cfg.chunker)
    retriever = Retriever(store, builder, llm, cfg.retriever.n_results)
    generator = DocumentGenerator(store, llm)
    itij      = ITIJScraper()

    _instances.update({
        "cfg": cfg, "embedder": embedder, "store": store,
        "builder": builder, "llm": llm, "chunker": chunker,
        "retriever": retriever, "generator": generator, "itij": itij,
    })


def get_cfg():       _init(); return _instances["cfg"]
def get_store():     _init(); return _instances["store"]
def get_retriever(): _init(); return _instances["retriever"]
def get_generator(): _init(); return _instances["generator"]
def get_itij():      _init(); return _instances["itij"]
def get_llm():       _init(); return _instances["llm"]
def get_chunker():   _init(); return _instances["chunker"]