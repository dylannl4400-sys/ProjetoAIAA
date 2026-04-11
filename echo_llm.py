from llm import LLM


class EchoLLM(LLM):
    """
    LLM stub for testing — returns the prompt unchanged.

    Use this during development to test the Retriever and PromptBuilder
    without needing Ollama installed or a GPU available. Lets you verify
    that the correct context is being assembled before connecting a real
    language model.

    The returned text is the full prompt, prefixed with a marker so it
    is obvious in logs that this is a stub response.

    Example:
        llm    = EchoLLM()
        answer = llm.generate("What is the statute of limitations?")
        # answer == "[ECHO] What is the statute of limitations?"
    """

    @property
    def model_name(self) -> str:
        return "echo-stub"

    def generate(self, prompt: str) -> str:
        return f"[ECHO]\n{prompt}"
