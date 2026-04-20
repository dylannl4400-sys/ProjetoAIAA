from collections import Counter

import pdfplumber

from chunker import Chunker


class StructureAwareChunker(Chunker):
    """
    Splits a PDF into chunks that respect its internal structure.

    Instead of splitting by character count, this chunker analyses the
    typographic properties of each line (font size, boldness) to detect
    section boundaries — independently of the actual text content.

    Strategy
    --------
    1. Extract all characters from the PDF via pdfplumber.
    2. Group characters into lines by vertical position.
    3. Identify the body font size as the most frequent size in the document.
    4. Treat any line whose size exceeds the body size as a section heading,
       assigning it a hierarchical level (1 = largest heading, 2 = next, …).
    5. Accumulate body lines into a chunk until the next heading is found.
    6. If an accumulated section exceeds max_section_chars, subdivide it
       with FixedChunker(chunk_size=max_section_chars, overlap=overlap)
       so that no chunk is too large for a reliable embedding.

    Each returned chunk includes structural metadata:
        section       : title of the section the chunk belongs to
        section_level : heading level of that section (1, 2, …)
        page_start    : first page of the chunk (1-based)
        chunk_index   : position among all chunks produced (0-based)
        chunk_total   : total number of chunks produced

    Args:
        max_section_chars: Maximum characters for a single section chunk.
                           Sections larger than this are further subdivided.
        overlap:           Character overlap used when subdividing long sections.

    Limitations
    -----------
    Requires a native (digitally created) PDF. Scanned PDFs need OCR
    pre-processing (e.g. pytesseract) before being passed to this chunker.

    The split() method accepts the PDF file path as `text` when used with
    PDFs. For plain-text input it falls back to FixedChunker behaviour so
    the interface remains compatible.

    Example:
        chunker = StructureAwareChunker(max_section_chars=1500, overlap=200)
        chunks  = chunker.split("path/to/acordao.pdf")
    """

    def __init__(
        self,
        max_section_chars: int = 1500,
        overlap: int = 200,
    ) -> None:
        if overlap >= max_section_chars:
            raise ValueError("overlap must be smaller than max_section_chars")
        self.max_section_chars = max_section_chars
        self.overlap = overlap

    # ------------------------------------------------------------------
    # Chunker interface
    # ------------------------------------------------------------------

    def split(self, text: str) -> list[dict]:
        """
        Args:
            text: Path to a PDF file OR raw text string.
                  When a PDF path is provided the structure is inferred
                  from typographic properties.
                  When plain text is provided the chunker falls back to
                  fixed-size splitting (no structural metadata).
        """
        if text.strip().endswith(".pdf"):
            return self._split_pdf(text.strip())
        return self._split_plain_text(text)

    # ------------------------------------------------------------------
    # PDF path
    # ------------------------------------------------------------------

    def _split_pdf(self, pdf_path: str) -> list[dict]:
        blocks = self._extract_blocks(pdf_path)
        sections = self._blocks_to_sections(blocks)
        return self._sections_to_chunks(sections)

    # ------------------------------------------------------------------
    # Plain-text fallback (keeps interface compatible)
    # ------------------------------------------------------------------

    def _split_plain_text(self, text: str) -> list[dict]:
        from fixed_chunker import FixedChunker

        inner = FixedChunker(
            chunk_size=self.max_section_chars,
            overlap=self.overlap,
        )
        chunks = inner.split(text)
        for chunk in chunks:
            chunk.setdefault("section", "unknown")
            chunk.setdefault("section_level", 0)
            chunk.setdefault("page_start", None)
        return chunks

    # ------------------------------------------------------------------
    # Step 1 — extract typed blocks from PDF
    # ------------------------------------------------------------------

    def _extract_blocks(self, pdf_path: str) -> list[dict]:
        """Return a flat list of line-level blocks with size, font, page."""
        all_lines: list[dict] = []
        size_counter: Counter = Counter()

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                chars = page.chars
                if not chars:
                    continue
                for line in _group_chars_into_lines(chars):
                    line["page"] = page_num
                    size_counter[round(line["size"])] += 1
                    all_lines.append(line)

        if not all_lines:
            return []

        # Body size = most frequent font size in the document
        body_size: int = size_counter.most_common(1)[0][0]

        # Heading sizes = everything above body, sorted largest→smallest
        heading_sizes: list[int] = sorted(
            (s for s in size_counter if s > body_size),
            reverse=True,
        )

        for line in all_lines:
            size = round(line["size"])
            if size in heading_sizes:
                line["level"] = heading_sizes.index(size) + 1
            else:
                line["level"] = 0  # body text

        return all_lines

    # ------------------------------------------------------------------
    # Step 2 — group blocks into sections
    # ------------------------------------------------------------------

    def _blocks_to_sections(self, blocks: list[dict]) -> list[dict]:
        """Accumulate body lines under their nearest heading."""
        sections: list[dict] = []
        current_title = "preamble"
        current_level = 0
        current_page = blocks[0]["page"] if blocks else 1
        current_lines: list[str] = []

        for block in blocks:
            if block["level"] > 0:                      # heading line
                if current_lines:
                    sections.append({
                        "title":      current_title,
                        "level":      current_level,
                        "page_start": current_page,
                        "text":       "\n".join(current_lines).strip(),
                    })
                current_title = block["text"]
                current_level = block["level"]
                current_page  = block["page"]
                current_lines = []
            else:                                        # body line
                if block["text"].strip():
                    current_lines.append(block["text"])

        if current_lines:
            sections.append({
                "title":      current_title,
                "level":      current_level,
                "page_start": current_page,
                "text":       "\n".join(current_lines).strip(),
            })

        return sections

    # ------------------------------------------------------------------
    # Step 3 — convert sections to chunks (subdivide if too long)
    # ------------------------------------------------------------------

    def _sections_to_chunks(self, sections: list[dict]) -> list[dict]:
        from fixed_chunker import FixedChunker

        subdivider = FixedChunker(
            chunk_size=self.max_section_chars,
            overlap=self.overlap,
        )

        raw: list[dict] = []
        for section in sections:
            if not section["text"]:
                continue

            if len(section["text"]) <= self.max_section_chars:
                raw.append({
                    "text":          section["text"],
                    "section":       section["title"],
                    "section_level": section["level"],
                    "page_start":    section["page_start"],
                })
            else:
                # Section too long — subdivide while keeping metadata
                sub_chunks = subdivider.split(section["text"])
                for sub in sub_chunks:
                    raw.append({
                        "text":          sub["text"],
                        "section":       section["title"],
                        "section_level": section["level"],
                        "page_start":    section["page_start"],
                    })

        total = len(raw)
        for i, chunk in enumerate(raw):
            chunk["chunk_index"] = i
            chunk["chunk_total"] = total

        return raw


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _group_chars_into_lines(chars: list[dict]) -> list[dict]:
    """Group individual PDF characters into text lines by vertical position."""
    if not chars:
        return []

    lines: list[dict] = []
    current: list[dict] = [chars[0]]

    for char in chars[1:]:
        if abs(char["y0"] - current[-1]["y0"]) < 2:
            current.append(char)
        else:
            lines.append(_chars_to_line(current))
            current = [char]

    if current:
        lines.append(_chars_to_line(current))

    return [line for line in lines if line["text"].strip()]


def _chars_to_line(chars: list[dict]) -> dict:
    text  = "".join(c["text"] for c in chars).strip()
    sizes = [c["size"]     for c in chars if c.get("size")]
    fonts = [c["fontname"] for c in chars if c.get("fontname")]
    return {
        "text": text,
        "size": max(sizes) if sizes else 0,
        "font": max(set(fonts), key=fonts.count) if fonts else "",
    }
