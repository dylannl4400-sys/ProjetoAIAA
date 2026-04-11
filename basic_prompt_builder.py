from prompt_builder import PromptBuilder


class BasicPromptBuilder(PromptBuilder):
    """
    Simple, language-agnostic prompt template.

    Assembles the retrieved chunks as a numbered context block followed
    by the user's question. No domain-specific instructions are added.
    Use as a baseline when evaluating prompt quality.

    Output format
    -------------
        Use the following context to answer the question.

        [1] (score: 0.92)
        <chunk text>

        [2] (score: 0.85)
        <chunk text>

        ...

        Question: <question>
        Answer:

    Args:
        max_chunks: Maximum number of chunks to include in the prompt.
                    Lower values produce shorter prompts; higher values
                    give the LLM more context. Default: 5.
    """

    def __init__(self, max_chunks: int = 5) -> None:
        self.max_chunks = max_chunks

    def build(self, question: str, chunks: list[dict]) -> str:
        context_lines = ["Use the following context to answer the question.\n"]

        for i, chunk in enumerate(chunks[: self.max_chunks], start=1):
            score = chunk.get("score", 0.0)
            context_lines.append(f"[{i}] (score: {score:.2f})")
            context_lines.append(chunk["text"])
            context_lines.append("")   # blank line between chunks

        context_lines.append(f"Question: {question}")
        context_lines.append("Answer:")

        return "\n".join(context_lines)
