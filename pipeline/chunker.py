from abc import ABC, abstractmethod


class Chunker(ABC):
    """
    Abstract base class for text chunking strategies.

    A chunker receives raw text and returns a list of chunks,
    each with its content and any structural metadata inferred
    during the splitting process.

    Implementations
    ---------------
    FixedChunker          : splits by character count with optional overlap.
    StructureAwareChunker : splits by typographic/structural boundaries in PDFs.
    """

    @abstractmethod
    def split(self, text: str) -> list[dict]:
        """
        Split text into chunks.

        Args:
            text: Raw text content to split.

        Returns:
            List of dicts, each with at minimum:
                {
                    "text":        str,  # chunk content
                    "chunk_index": int,  # position in the sequence (0-based)
                    "chunk_total": int,  # total number of chunks produced
                    # implementations may add extra keys:
                    # "section", "level", "page", ...
                }
        """
