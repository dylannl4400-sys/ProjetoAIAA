from abc import ABC, abstractmethod


class Embedder(ABC):
    """
    Abstract base class for text embedding models.

    An embedder converts a string of text into a dense vector (list of floats)
    that captures its semantic meaning. The vector is then stored and searched
    in the VectorStore.

    All implementations must produce vectors of the same fixed dimension for
    a given instance, declared via the `dimension` property.

    Implementations
    ---------------
    SentenceTransformerEmbedder : local model via sentence-transformers (default).
    OllamaEmbedder              : local model served by Ollama (no internet needed).

    Contract
    --------
    - embed(text)  → list[float] of length == self.dimension
    - dimension    → int  (must be constant for a given instance)
    - model_name   → str  (human-readable identifier of the model in use)
    
    "embedder": {
    "provider": "sentence_transformer",
    "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
    "base_url": "http://localhost:11434"
  },
    
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Encode a single text string into a dense vector.

        Args:
            text: Raw text to embed (chunk content or query).

        Returns:
            List of floats of length self.dimension.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Fixed size of the vectors produced by this embedder."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable name/identifier of the underlying model."""
