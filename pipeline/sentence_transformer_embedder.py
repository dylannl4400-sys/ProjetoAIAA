from sentence_transformers import SentenceTransformer

from embedder import Embedder


class SentenceTransformerEmbedder(Embedder):
    """
    Local embedding model via the sentence-transformers library.

    No internet connection is needed after the first run — the model
    is downloaded once and cached locally by the library.

    Recommended models for legal Portuguese text
    ---------------------------------------------
    "all-MiniLM-L6-v2"          : 384-dim, fast, good baseline (English).
    "paraphrase-multilingual-MiniLM-L12-v2"
                                 : 384-dim, multilingual, handles Portuguese.
    "distiluse-base-multilingual-cased-v2"
                                 : 512-dim, stronger multilingual quality.
    "intfloat/multilingual-e5-base"
                                 : 768-dim, state-of-the-art multilingual.

    For AIAA, start with "paraphrase-multilingual-MiniLM-L12-v2" and
    evaluate with eval_rag.py before upgrading to a heavier model.

    Args:
        model_name: HuggingFace model identifier or local path.

    Example:
        embedder = SentenceTransformerEmbedder(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        vector = embedder.embed("O réu foi absolvido por falta de prova.")
        print(len(vector))  # 384
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ) -> None:
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    # ------------------------------------------------------------------
    # Embedder interface
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name
