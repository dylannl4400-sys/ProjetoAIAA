from chunker import Chunker


class FixedChunker(Chunker):
    """
    Splits text into fixed-size character chunks with optional overlap.

    This is the simplest chunking strategy and the recommended starting
    point. Use the eval_rag.py script to find the best (chunk_size, overlap)
    combination before considering more sophisticated strategies.

    Args:
        chunk_size: Maximum number of characters per chunk.
        overlap:    Number of characters shared between consecutive chunks.
                    Must be smaller than chunk_size.

    Example:
        chunker = FixedChunker(chunk_size=1000, overlap=200)
        chunks  = chunker.split(raw_text)
        # chunks[0] == {"text": "...", "chunk_index": 0, "chunk_total": 4}
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 200) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[dict]:
        raw_chunks: list[str] = []
        step = self.chunk_size - self.overlap
        start = 0

        while start < len(text):
            chunk = text[start : start + self.chunk_size].strip()
            if chunk:
                raw_chunks.append(chunk)
            start += step

        total = len(raw_chunks)
        return [
            {
                "text":        chunk,
                "chunk_index": i,
                "chunk_total": total,
            }
            for i, chunk in enumerate(raw_chunks)
        ]
