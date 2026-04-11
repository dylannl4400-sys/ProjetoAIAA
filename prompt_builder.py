from abc import ABC, abstractmethod


class PromptBuilder(ABC):
    """
    Abstract base class for prompt construction strategies.

    A PromptBuilder receives the user's question and the list of retrieved
    chunks from the VectorStore, and assembles them into a single prompt
    string ready to be sent to an LLM.

    Separating prompt construction from the Retriever allows iterating on
    prompt format independently — without touching retrieval or generation
    logic. Prompt format has a direct impact on answer quality and will
    require frequent tuning.

    Implementations
    ---------------
    BasicPromptBuilder : simple, language-agnostic template.
    LegalPromptBuilder : specialised for legal Portuguese context, instructs
                         the LLM to cite sources and use formal legal language.

    Contract
    --------
    build(question, chunks) → str
        question : the user's original question (plain text)
        chunks   : list of dicts as returned by VectorStore.search(),
                   each with keys: text, metadata, score
    """

    @abstractmethod
    def build(self, question: str, chunks: list[dict]) -> str:
        """
        Assemble a prompt from a question and retrieved context chunks.

        Args:
            question: The user's original question.
            chunks:   Retrieved chunks, each a dict with keys:
                        text     : chunk content
                        metadata : dict of document metadata
                        score    : float relevance score (0–1)

        Returns:
            A fully-formed prompt string ready to send to an LLM.
        """
