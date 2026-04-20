from abc import ABC, abstractmethod


class LLM(ABC):
    """
    Abstract base class for language model implementations.

    An LLM receives a fully-formed prompt string and returns a generated
    text response. The prompt construction is handled externally by a
    PromptBuilder — this class is only responsible for inference.

    Implementations
    ---------------
    OllamaLLM : runs an open-source model locally via Ollama (production).
    EchoLLM   : returns the prompt unchanged — useful for testing the
                Retriever and PromptBuilder without needing a GPU or Ollama.

    Contract
    --------
    - generate(prompt) → str
    - model_name       → str
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a text response for the given prompt.

        Args:
            prompt: Fully-formed prompt string, including context and question.

        Returns:
            Generated text response as a plain string.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable name/identifier of the underlying model."""
