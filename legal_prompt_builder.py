from prompt_builder import PromptBuilder


class LegalPromptBuilder(PromptBuilder):
    """
    Prompt template specialised for legal Portuguese context.

    Instructs the LLM to:
    - respond in formal legal Portuguese
    - ground its answer exclusively in the provided sources
    - cite sources by their index number [1], [2], ...
    - explicitly state when the context is insufficient to answer
    - never fabricate legal references or case numbers

    These constraints are critical for a legal assistant — hallucinated
    citations or invented statutes could have serious professional consequences.

    Output format
    -------------
        És um assistente jurídico especializado em direito português. ...

        FONTES JURÍDICAS DISPONÍVEIS:

        [1] Tipo: ruling | Tribunal: ... | Ano: ...
        <chunk text>

        ...

        QUESTÃO: <question>

        RESPOSTA (em português, citando as fontes pelo número):

    Args:
        max_chunks:    Maximum number of chunks to include. Default: 5.
        min_score:     Minimum relevance score to include a chunk.
                       Chunks below this threshold are silently dropped.
                       Default: 0.3.
    """

    SYSTEM_INSTRUCTION = (
        "És um assistente jurídico especializado em direito português. "
        "Responde sempre em português europeu formal e jurídico. "
        "Baseia a tua resposta exclusivamente nas fontes jurídicas fornecidas. "
        "Cita sempre as fontes pelo número entre parênteses rectos, e.g. [1], [2]. "
        "Se as fontes fornecidas não forem suficientes para responder à questão, "
        "indica explicitamente que a informação não está disponível no contexto fornecido. "
        "Nunca inventes referências, números de processo, artigos ou datas."
    )

    def __init__(self, max_chunks: int = 5, min_score: float = 0.3) -> None:
        self.max_chunks = max_chunks
        self.min_score  = min_score

    def build(self, question: str, chunks: list[dict]) -> str:
        # Filter by minimum relevance score
        filtered = [
            c for c in chunks
            if c.get("score", 0.0) >= self.min_score
        ][: self.max_chunks]

        lines = [
            self.SYSTEM_INSTRUCTION,
            "",
            "FONTES JURÍDICAS DISPONÍVEIS:",
            "",
        ]

        if not filtered:
            lines.append("(Não foram encontradas fontes suficientemente relevantes.)")
        else:
            for i, chunk in enumerate(filtered, start=1):
                meta  = chunk.get("metadata", {})
                score = chunk.get("score", 0.0)

                # Build a concise source header from available metadata
                header_parts = []
                if "type"    in meta: header_parts.append(f"Tipo: {meta['type']}")
                if "court"   in meta: header_parts.append(f"Tribunal: {meta['court']}")
                if "year"    in meta: header_parts.append(f"Ano: {meta['year']}")
                if "section" in meta: header_parts.append(f"Secção: {meta['section']}")
                header_parts.append(f"Relevância: {score:.0%}")

                lines.append(f"[{i}] {' | '.join(header_parts)}")
                lines.append(chunk["text"])
                lines.append("")

        lines += [
            f"QUESTÃO: {question}",
            "",
            "RESPOSTA (em português, citando as fontes pelo número):",
        ]

        return "\n".join(lines)
