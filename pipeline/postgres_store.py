import json
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from embedder import Embedder
from sentence_transformer_embedder import SentenceTransformerEmbedder
from vector_store import VectorStore


class PostgresStore(VectorStore):
    """
    VectorStore implementation backed by PostgreSQL + pgvector.

    The Embedder is injected via the constructor — same pattern as
    ChromaStore — ensuring the embedding model is fully decoupled from
    the storage backend.

    Args:
        embedder:   Any Embedder implementation. Must produce vectors of
                    the same dimension as those already stored in the table.
        dsn:        PostgreSQL connection string.
        table_name: Name of the documents table (created automatically).

    Example:
        embedder = OllamaEmbedder("nomic-embed-text")
        store    = PostgresStore(embedder=embedder, dsn="postgresql://localhost/aiaa")
        store.add("O réu foi absolvido.", {"type": "ruling"})
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        dsn: str = "postgresql://localhost/aiaa",
        table_name: str = "legal_docs",
    ) -> None:
        self._embedder = embedder or SentenceTransformerEmbedder()
        self._conn = psycopg2.connect(dsn)
        self._table = table_name
        self._setup()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        """Create the pgvector extension and documents table if needed."""
        dim = self._embedder.dimension
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id        TEXT PRIMARY KEY,
                    content   TEXT          NOT NULL,
                    metadata  JSONB         NOT NULL DEFAULT '{{}}',
                    embedding vector({dim}) NOT NULL
                );
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {self._table}_embedding_idx
                ON {self._table} USING ivfflat (embedding vector_cosine_ops);
            """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # VectorStore interface
    # ------------------------------------------------------------------

    def add(self, text: str, metadata: dict) -> str:
        doc_id  = str(uuid.uuid4())
        vector  = self._embedder.embed(text)
        with self._conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self._table} (id, content, metadata, embedding) "
                "VALUES (%s, %s, %s::jsonb, %s::vector)",
                (doc_id, text, json.dumps(metadata), vector),
            )
        self._conn.commit()
        return doc_id

    def search(self, query: str, filters: dict | None = None, n: int = 5) -> list[dict]:
        vector = self._embedder.embed(query)

        where_clause = ""
        params: list = [vector, n]
        if filters:
            conditions = [f"metadata->>'{k}' = %s" for k in filters]
            where_clause = "WHERE " + " AND ".join(conditions)
            params = [vector] + list(filters.values()) + [n]

        sql = f"""
            SELECT id,
                   content,
                   metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM   {self._table}
            {where_clause}
            ORDER  BY score DESC
            LIMIT  %s;
        """
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [
            {
                "id":       row["id"],
                "text":     row["content"],
                "metadata": row["metadata"],
                "score":    float(row["score"]),
            }
            for row in rows
        ]

    def remove(self, doc_id: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._table} WHERE id = %s", (doc_id,))
        self._conn.commit()

    def count(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._table}")
            return cur.fetchone()[0]

    def close(self) -> None:
        self._conn.close()
