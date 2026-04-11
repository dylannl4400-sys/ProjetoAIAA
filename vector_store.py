from abc import ABC, abstractmethod
from typing import Any


class VectorStore(ABC):
    """Abstract base class for vector store implementations."""

    @abstractmethod
    def add(self, text: str, metadata: dict) -> str:
        """
        Embed and store a document.

        Args:
            text:     Raw text content of the document.
            metadata: Arbitrary key-value pairs (e.g. type, court, date).

        Returns:
            The ID assigned to the stored document.
        """

    @abstractmethod
    def search(self, query: str, filters: dict | None = None, n: int = 5) -> list[dict]:
        """
        Embed a query and return the most similar documents.

        Args:
            query:   Natural language query.
            filters: Optional metadata filters (e.g. {"type": "ruling"}).
            n:       Number of results to return, already ranked by relevance.

        Returns:
            List of dicts with keys: id, text, metadata, score.
        """

    @abstractmethod
    def remove(self, doc_id: str) -> None:
        """
        Remove a document from the store by ID.

        Args:
            doc_id: ID of the document to remove.
        """

    @abstractmethod
    def count(self) -> int:
        """Return the total number of documents currently stored."""
