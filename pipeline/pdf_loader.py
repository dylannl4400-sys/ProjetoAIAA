"""
pdf_loader.py

Reads a PDF file and produces a plain-text string ready to be passed
to any Chunker implementation.

Two extraction modes are available:

  TextLoader   — extracts raw text page by page (fast, works for any PDF).
                 Use this with FixedChunker.

  PlumberLoader — extracts text while preserving font/size information
                 needed by StructureAwareChunker. Also returns a
                 `chars` list with per-character metadata.
                 Use this with StructureAwareChunker.

Both loaders also infer basic document metadata (title, number of pages,
file name) that can be merged with the chunk metadata before indexing.

Usage
-----
    # With FixedChunker
    loader = TextLoader("acordao_01.pdf")
    text   = loader.load()
    meta   = loader.metadata()

    chunker = FixedChunker(chunk_size=1000, overlap=200)
    chunks  = chunker.split(text)
    for chunk in chunks:
        store.add(chunk["text"], {**meta, **chunk})

    # With StructureAwareChunker
    loader  = PlumberLoader("acordao_01.pdf")
    # pass the file path directly — StructureAwareChunker opens it internally
    chunker = StructureAwareChunker(max_section_chars=1500, overlap=200)
    chunks  = chunker.split(loader.path)
"""

from abc import ABC, abstractmethod
import os
import pdfplumber


class PDFLoader(ABC):
    """Abstract base class for PDF loaders."""

    def __init__(self, path: str) -> None:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"PDF not found: {path}")
        if not path.lower().endswith(".pdf"):
            raise ValueError(f"Expected a .pdf file, got: {path}")
        self.path = path

    @abstractmethod
    def load(self) -> str:
        """Extract and return the full text content of the PDF."""

    def metadata(self) -> dict:
        """
        Return basic document metadata inferred from the file.

        Keys always present:
            filename   : base name of the file (e.g. "acordao_01.pdf")
            filepath   : absolute path to the file
            num_pages  : total number of pages
            source     : always "pdf"
        """
        with pdfplumber.open(self.path) as pdf:
            num_pages = len(pdf.pages)

        return {
            "filename":  os.path.basename(self.path),
            "filepath":  os.path.abspath(self.path),
            "num_pages": num_pages,
            "source":    "pdf",
        }


class TextLoader(PDFLoader):
    """
    Extracts plain text from a PDF using pdfplumber.

    Joins all pages with a newline separator. Best used together with
    FixedChunker, which only needs raw text.

    Args:
        path:           Path to the PDF file.
        page_separator: String inserted between pages (default: newline).
    """

    def __init__(self, path: str, page_separator: str = "\n") -> None:
        super().__init__(path)
        self.page_separator = page_separator

    def load(self) -> str:
        pages = []
        with pdfplumber.open(self.path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    pages.append(text.strip())
        return self.page_separator.join(pages)


class PlumberLoader(PDFLoader):
    """
    Extracts text from a PDF while preserving typographic metadata
    (font name, font size, position) per character.

    The load() method returns plain text (same interface as TextLoader).
    The chars() method returns the raw per-character data needed by
    StructureAwareChunker internally — you do not need to call it
    directly when using StructureAwareChunker, since that chunker
    opens the PDF itself via the file path.

    Use PlumberLoader when you want to inspect the typographic
    properties of a document before deciding which chunker to use.
    """

    def load(self) -> str:
        """Return plain text (same as TextLoader)."""
        pages = []
        with pdfplumber.open(self.path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    pages.append(text.strip())
        return "\n".join(pages)

    def font_sizes(self) -> dict[int, int]:
        """
        Return a frequency map of font sizes found in the document.

        Useful for previewing the typographic structure before chunking.

        Returns:
            Dict mapping font_size → number of characters with that size.

        Example output:
            {10: 4821, 13: 312, 11: 198, 9: 47}
            → body is size 10; sizes 11 and 13 are likely headings.
        """
        from collections import Counter
        counter: Counter = Counter()
        with pdfplumber.open(self.path) as pdf:
            for page in pdf.pages:
                for char in page.chars:
                    size = char.get("size")
                    if size:
                        counter[round(size)] += 1
        return dict(counter.most_common())
