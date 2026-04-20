import json
import urllib.request

from embedder import Embedder


class OllamaEmbedder(Embedder):
    """
    Embedding model served locally by Ollama.

    Ollama runs open-source models (e.g. nomic-embed-text, mxbai-embed-large)
    entirely on your machine — no API keys, no internet, no usage costs.
    This aligns with the AIAA requirement for open-source LLM tooling.

    Prerequisites
    -------------
    1. Install Ollama: https://ollama.com
    2. Pull an embedding model:
           ollama pull nomic-embed-text
    3. Ollama must be running before calling embed():
           ollama serve      (or it starts automatically on most platforms)

    Recommended models
    ------------------
    "nomic-embed-text"      : 768-dim, fast, good English/multilingual quality.
    "mxbai-embed-large"     : 1024-dim, stronger, slower.
    "snowflake-arctic-embed": 1024-dim, state-of-the-art retrieval quality.

    Args:
        model_name:  Name of the Ollama model to use (must be pulled first).
        base_url:    Base URL of the Ollama API (default: localhost:11434).

    Example:
        embedder = OllamaEmbedder("nomic-embed-text")
        vector   = embedder.embed("O réu foi absolvido por falta de prova.")
        print(len(vector))  # 768
    """

    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._dimension: int | None = None   # resolved lazily on first embed()

    # ------------------------------------------------------------------
    # Embedder interface
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self._model_name, "prompt": text}).encode()
        req = urllib.request.Request(
            url=f"{self._base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            body = json.loads(response.read())

        vector: list[float] = body["embedding"]

        # Cache dimension on first successful call
        if self._dimension is None:
            self._dimension = len(vector)

        return vector

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Trigger a minimal embed to resolve dimension
            self.embed(" ")
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name
