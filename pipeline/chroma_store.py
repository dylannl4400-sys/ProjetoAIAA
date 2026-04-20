# import uuid

# import chromadb

# from embedder import Embedder
# from sentence_transformer_embedder import SentenceTransformerEmbedder
# from vector_store import VectorStore


# class ChromaStore(VectorStore):
#     """
#     VectorStore implementation backed by ChromaDB.

#     The Embedder is injected via the constructor — it is never created
#     internally. This decouples the embedding model from the storage
#     backend so both can be swapped independently.

#     Args:
#         embedder:          Any Embedder implementation. Defaults to
#                            SentenceTransformerEmbedder with the multilingual
#                            model recommended for Portuguese legal text.
#         collection_name:   Name of the ChromaDB collection.
#         persist_directory: Directory where ChromaDB persists data to disk.

#     Example:
#         embedder = OllamaEmbedder("nomic-embed-text")
#         store    = ChromaStore(embedder=embedder)
#         store.add("O réu foi absolvido.", {"type": "ruling"})
#     """

#     def __init__(
#         self,
#         embedder: Embedder | None = None,
#         collection_name: str = "legal_docs",
#         persist_directory: str = "./chroma_db",
#     ) -> None:
#         self._embedder = embedder or SentenceTransformerEmbedder()
#         self._client = chromadb.PersistentClient(path=persist_directory)

#         # Use a custom embedding function that delegates to our Embedder
#         self._collection = self._client.get_or_create_collection(
#             name=collection_name,
#             embedding_function=_EmbedderAdapter(self._embedder),
#             metadata={"hnsw:space": "cosine"},
#         )

#     # ------------------------------------------------------------------
#     # VectorStore interface
#     # ------------------------------------------------------------------

#     def add(self, text: str, metadata: dict) -> str:
#         doc_id = str(uuid.uuid4())
#         self._collection.add(
#             ids=[doc_id],
#             documents=[text],
#             metadatas=[metadata],
#         )
#         return doc_id

#     def search(self, query: str, filters: dict | None = None, n: int = 5) -> list[dict]:
#         kwargs: dict = {"query_texts": [query], "n_results": n}
#         if filters:
#             kwargs["where"] = filters

#         results = self._collection.query(**kwargs)

#         return [
#             {
#                 "id":       results["ids"][0][i],
#                 "text":     results["documents"][0][i],
#                 "metadata": results["metadatas"][0][i],
#                 "score":    1 - results["distances"][0][i],   # cosine similarity
#             }
#             for i in range(len(results["ids"][0]))
#         ]

#     def remove(self, doc_id: str) -> None:
#         self._collection.delete(ids=[doc_id])

#     def count(self) -> int:
#         return self._collection.count()


# # ---------------------------------------------------------------------------
# # Internal adapter — wraps our Embedder in ChromaDB's expected interface
# # ---------------------------------------------------------------------------

# # class _EmbedderAdapter:
# #     """Adapts our Embedder ABC to the ChromaDB embedding function protocol."""

# #     def __init__(self, embedder: Embedder) -> None:
# #         self._embedder = embedder
        
# #     # def name(self) -> str:
# #     #     return f"aiaa-embedder:{self._embedder.model_name}"

# #     def __call__(self, input: list[str]) -> list[list[float]]:   # noqa: A002
# #         return [self._embedder.embed(text) for text in input]

# class _EmbedderAdapter:
#     """Adapts our Embedder ABC to the ChromaDB embedding function protocol.

#     ChromaDB's interface has changed across versions. This adapter covers
#     all three method signatures ChromaDB may call:

#         name()              -> str            version check / consistency guard
#         embed_documents()   -> list[list[float]]  called when indexing (add)
#         embed_query()       -> list[list[float]]  called when searching (query)
#         __call__()          -> list[list[float]]  fallback for older versions

#     name() returns the model identifier so that ChromaDB raises a clear
#     conflict error if you try to search a collection with a different
#     embedding model than the one used to index it.
#     """

#     def __init__(self, embedder: Embedder) -> None:
#         self._embedder = embedder

#     def name(self) -> str:
#         return f"aiaa-embedder:{self._embedder.model_name}"

#     def embed_documents(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

#     def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

#     def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]
# import uuid

# import chromadb

# from embedder import Embedder
# from sentence_transformer_embedder import SentenceTransformerEmbedder
# from vector_store import VectorStore


# class ChromaStore(VectorStore):
#     """
#     VectorStore implementation backed by ChromaDB.

#     The Embedder is injected via the constructor — it is never created
#     internally. This decouples the embedding model from the storage
#     backend so both can be swapped independently.

#     Args:
#         embedder:          Any Embedder implementation. Defaults to
#                            SentenceTransformerEmbedder with the multilingual
#                            model recommended for Portuguese legal text.
#         collection_name:   Name of the ChromaDB collection.
#         persist_directory: Directory where ChromaDB persists data to disk.

#     Example:
#         embedder = OllamaEmbedder("nomic-embed-text")
#         store    = ChromaStore(embedder=embedder)
#         store.add("O réu foi absolvido.", {"type": "ruling"})
#     """

#     def __init__(
#         self,
#         embedder: Embedder | None = None,
#         collection_name: str = "legal_docs",
#         persist_directory: str = "./chroma_db",
#     ) -> None:
#         self._embedder = embedder or SentenceTransformerEmbedder()
#         self._client = chromadb.PersistentClient(path=persist_directory)

#         self._collection = self._client.get_or_create_collection(
#             name=collection_name,
#             embedding_function=_EmbedderAdapter(self._embedder),
#             metadata={"hnsw:space": "cosine"},
#         )

#     # ------------------------------------------------------------------
#     # VectorStore interface
#     # ------------------------------------------------------------------

#     def add(self, text: str, metadata: dict) -> str:
#         doc_id = str(uuid.uuid4())
#         self._collection.add(
#             ids=[doc_id],
#             documents=[text],
#             metadatas=[metadata],
#         )
#         return doc_id

#     def search(self, query: str, filters: dict | None = None, n: int = 5) -> list[dict]:
#         kwargs: dict = {"query_texts": [query], "n_results": n}
#         if filters:
#             kwargs["where"] = filters

#         results = self._collection.query(**kwargs)

#         return [
#             {
#                 "id":       results["ids"][0][i],
#                 "text":     results["documents"][0][i],
#                 "metadata": results["metadatas"][0][i],
#                 "score":    1 - results["distances"][0][i],
#             }
#             for i in range(len(results["ids"][0]))
#         ]

#     def remove(self, doc_id: str) -> None:
#         self._collection.delete(ids=[doc_id])

#     def count(self) -> int:
#         return self._collection.count()

#     def close(self) -> None:
#         """
#         Release all file handles held by the ChromaDB client.

#         Must be called before deleting the persist_directory on Windows,
#         where open SQLite handles block directory removal (WinError 32).
#         Safe to call on all platforms.
#         """
#         self._collection = None   # drop reference to collection first
#         try:
#             # clear_system_cache() releases the SQLite connection pool
#             # kept alive by ChromaDB's internal singleton
#             chromadb.api.client.SharedSystemClient.clear_system_cache()
#         except Exception:
#             try:
#                 self._client.clear_system_cache()
#             except Exception:
#                 pass
#         self._client = None       # type: ignore[assignment]


# # ---------------------------------------------------------------------------
# # Internal adapter — wraps our Embedder in ChromaDB's expected interface
# # ---------------------------------------------------------------------------

# class _EmbedderAdapter:
#     """Adapts our Embedder ABC to the ChromaDB embedding function protocol.

#     ChromaDB's interface has changed across versions. This adapter covers
#     all three method signatures ChromaDB may call:

#         name()              -> str            version check / consistency guard
#         embed_documents()   -> list[list[float]]  called when indexing (add)
#         embed_query()       -> list[list[float]]  called when searching (query)
#         __call__()          -> list[list[float]]  fallback for older versions

#     name() returns the model identifier so that ChromaDB raises a clear
#     conflict error if you try to search a collection with a different
#     embedding model than the one used to index it.
#     """

#     def __init__(self, embedder: Embedder) -> None:
#         self._embedder = embedder

#     def name(self) -> str:
#         return f"aiaa-embedder:{self._embedder.model_name}"

#     def embed_documents(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

#     def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

#     def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

# import uuid

# import chromadb

# from embedder import Embedder
# from sentence_transformer_embedder import SentenceTransformerEmbedder
# from vector_store import VectorStore


# class ChromaStore(VectorStore):
#     """
#     VectorStore implementation backed by ChromaDB.

#     The Embedder is injected via the constructor — it is never created
#     internally. This decouples the embedding model from the storage
#     backend so both can be swapped independently.

#     Args:
#         embedder:          Any Embedder implementation. Defaults to
#                            SentenceTransformerEmbedder with the multilingual
#                            model recommended for Portuguese legal text.
#         collection_name:   Name of the ChromaDB collection.
#         persist_directory: Directory where ChromaDB persists data to disk.

#     Example:
#         embedder = OllamaEmbedder("nomic-embed-text")
#         store    = ChromaStore(embedder=embedder)
#         store.add("O réu foi absolvido.", {"type": "ruling"})
#     """

#     def __init__(
#         self,
#         embedder: Embedder | None = None,
#         collection_name: str = "legal_docs",
#         persist_directory: str = "./chroma_db",
#         ephemeral: bool = False,
#     ) -> None:
#         self._embedder = embedder or SentenceTransformerEmbedder()

#         # ephemeral=True → in-memory only (no files on disk, no WinError 32)
#         # Use this for evaluation/testing. Use False for production indexing.
#         if ephemeral:
#             self._client = chromadb.EphemeralClient()
#         else:
#             self._client = chromadb.PersistentClient(path=persist_directory)

#         self._collection = self._client.get_or_create_collection(
#             name=collection_name,
#             embedding_function=_EmbedderAdapter(self._embedder),
#             metadata={"hnsw:space": "cosine"},
#         )

#     # ------------------------------------------------------------------
#     # VectorStore interface
#     # ------------------------------------------------------------------

#     def add(self, text: str, metadata: dict) -> str:
#         doc_id = str(uuid.uuid4())
#         self._collection.add(
#             ids=[doc_id],
#             documents=[text],
#             metadatas=[metadata],
#         )
#         return doc_id

#     def search(self, query: str, filters: dict | None = None, n: int = 5) -> list[dict]:
#         kwargs: dict = {"query_texts": [query], "n_results": n}
#         if filters:
#             kwargs["where"] = filters

#         results = self._collection.query(**kwargs)

#         return [
#             {
#                 "id":       results["ids"][0][i],
#                 "text":     results["documents"][0][i],
#                 "metadata": results["metadatas"][0][i],
#                 "score":    1 - results["distances"][0][i],
#             }
#             for i in range(len(results["ids"][0]))
#         ]

#     def remove(self, doc_id: str) -> None:
#         self._collection.delete(ids=[doc_id])

#     def count(self) -> int:
#         return self._collection.count()

#     def close(self) -> None:
#         """
#         Release all file handles held by the ChromaDB client.

#         Must be called before deleting the persist_directory on Windows,
#         where open SQLite handles block directory removal (WinError 32).
#         Safe to call on all platforms.
#         """
#         self._collection = None   # drop reference to collection first
#         try:
#             # clear_system_cache() releases the SQLite connection pool
#             # kept alive by ChromaDB's internal singleton
#             chromadb.api.client.SharedSystemClient.clear_system_cache()
#         except Exception:
#             try:
#                 self._client.clear_system_cache()
#             except Exception:
#                 pass
#         self._client = None       # type: ignore[assignment]


# # ---------------------------------------------------------------------------
# # Internal adapter — wraps our Embedder in ChromaDB's expected interface
# # ---------------------------------------------------------------------------

# class _EmbedderAdapter:
#     """Adapts our Embedder ABC to the ChromaDB embedding function protocol.

#     ChromaDB's interface has changed across versions. This adapter covers
#     all three method signatures ChromaDB may call:

#         name()              -> str            version check / consistency guard
#         embed_documents()   -> list[list[float]]  called when indexing (add)
#         embed_query()       -> list[list[float]]  called when searching (query)
#         __call__()          -> list[list[float]]  fallback for older versions

#     name() returns the model identifier so that ChromaDB raises a clear
#     conflict error if you try to search a collection with a different
#     embedding model than the one used to index it.
#     """

#     def __init__(self, embedder: Embedder) -> None:
#         self._embedder = embedder

#     def name(self) -> str:
#         return f"aiaa-embedder:{self._embedder.model_name}"

#     def embed_documents(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

#     def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]

#     def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
#         return [self._embedder.embed(text) for text in input]
    
import uuid

import chromadb

from embedder import Embedder
from sentence_transformer_embedder import SentenceTransformerEmbedder
from vector_store import VectorStore


class ChromaStore(VectorStore):
    """
    VectorStore implementation backed by ChromaDB.

    The Embedder is injected via the constructor — it is never created
    internally. This decouples the embedding model from the storage
    backend so both can be swapped independently.

    Args:
        embedder:          Any Embedder implementation. Defaults to
                           SentenceTransformerEmbedder with the multilingual
                           model recommended for Portuguese legal text.
        collection_name:   Name of the ChromaDB collection.
        persist_directory: Directory where ChromaDB persists data to disk.

    Example:
        embedder = OllamaEmbedder("nomic-embed-text")
        store    = ChromaStore(embedder=embedder)
        store.add("O réu foi absolvido.", {"type": "ruling"})
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        collection_name: str = "legal_docs",
        persist_directory: str = "./chroma_db",
        ephemeral: bool = False,
    ) -> None:
        self._embedder = embedder or SentenceTransformerEmbedder()

        # ephemeral=True → in-memory only (no files on disk, no WinError 32)
        # Use this for evaluation/testing. Use False for production indexing.
        if ephemeral:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(path=persist_directory)

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=_EmbedderAdapter(self._embedder),
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # VectorStore interface
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_metadata(metadata: dict) -> dict:
        """
        ChromaDB only accepts str, int, float, bool as metadata values.
        Convert or drop anything else (None, list, dict, etc.).
        """
        clean = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            elif v is None:
                clean[k] = ""
            elif isinstance(v, list):
                clean[k] = ", ".join(str(i) for i in v)
            else:
                clean[k] = str(v)
        return clean

    def add(self, text: str, metadata: dict) -> str:
        doc_id = str(uuid.uuid4())
        self._collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[self._sanitize_metadata(metadata)],
        )
        return doc_id

    def search(self, query: str, filters: dict | None = None, n: int = 5) -> list[dict]:
        kwargs: dict = {"query_texts": [query], "n_results": n}
        if filters:
            kwargs["where"] = filters

        results = self._collection.query(**kwargs)

        return [
            {
                "id":       results["ids"][0][i],
                "text":     results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score":    1 - results["distances"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    def remove(self, doc_id: str) -> None:
        self._collection.delete(ids=[doc_id])

    def count(self) -> int:
        return self._collection.count()

    def close(self) -> None:
        """
        Release all file handles held by the ChromaDB client.

        Must be called before deleting the persist_directory on Windows,
        where open SQLite handles block directory removal (WinError 32).
        Safe to call on all platforms.
        """
        self._collection = None   # drop reference to collection first
        try:
            # clear_system_cache() releases the SQLite connection pool
            # kept alive by ChromaDB's internal singleton
            chromadb.api.client.SharedSystemClient.clear_system_cache()
        except Exception:
            try:
                self._client.clear_system_cache()
            except Exception:
                pass
        self._client = None       # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Internal adapter — wraps our Embedder in ChromaDB's expected interface
# ---------------------------------------------------------------------------

class _EmbedderAdapter:
    """Adapts our Embedder ABC to the ChromaDB embedding function protocol.

    ChromaDB's interface has changed across versions. This adapter covers
    all three method signatures ChromaDB may call:

        name()              -> str            version check / consistency guard
        embed_documents()   -> list[list[float]]  called when indexing (add)
        embed_query()       -> list[list[float]]  called when searching (query)
        __call__()          -> list[list[float]]  fallback for older versions

    name() returns the model identifier so that ChromaDB raises a clear
    conflict error if you try to search a collection with a different
    embedding model than the one used to index it.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def name(self) -> str:
        return f"aiaa-embedder:{self._embedder.model_name}"

    def embed_documents(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return [self._embedder.embed(text) for text in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return [self._embedder.embed(text) for text in input]

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return [self._embedder.embed(text) for text in input]