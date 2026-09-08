"""Deterministic, paragraph-first archival text chunking."""
from __future__ import annotations

import re
from dataclasses import dataclass

CHUNKING_VERSION = "paragraph-v1"

@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    section_heading: str | None = None
    page: int | None = None

def _split_long(text: str, maximum: int) -> list[str]:
    """Split only an oversized paragraph, preferring sentence/word boundaries."""
    result = []
    text = text.strip()
    while len(text) > maximum:
        window = text[:maximum + 1]
        cut = max(window.rfind("\n"), window.rfind(". "), window.rfind("! "), window.rfind("? "), window.rfind(" "))
        if cut <= 0:
            cut = maximum
        else:
            cut += 1
        result.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        result.append(text)
    return result

def chunk_text(text: str, max_chars: int, min_chars: int, overlap_chars: int) -> list[Chunk]:
    """Keep paragraphs together wherever possible and produce stable output."""
    if max_chars <= 0 or min_chars > max_chars or overlap_chars >= max_chars:
        raise ValueError("invalid chunking configuration")
    # PyMuPDF Phase 1 extraction separates pages with these stable markers.
    pages = re.split(r"(?=\[Page\s+\d+\])", text)
    heading = None
    units: list[tuple[str, str | None, int | None]] = []
    for page_text in pages:
      marker = re.match(r"\[Page\s+(\d+)\]\s*", page_text)
      page = int(marker.group(1)) if marker else None
      page_text = page_text[marker.end():] if marker else page_text
      paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", page_text) if p.strip()]
      for paragraph in paragraphs:
        # Markdown headings and short, title-like standalone lines are provenance,
        # not content to blend into an unrelated preceding section.
        plain = paragraph.lstrip("#").strip()
        if (paragraph.startswith("#") or (len(plain) < 100 and "\n" not in plain and plain.isupper())):
            heading = plain
            continue
        units.extend((piece, heading, page) for piece in _split_long(paragraph, max_chars))
    chunks: list[tuple[str, str | None, int | None]] = []
    current = ""
    current_heading = None
    current_page = None
    for unit, unit_heading, unit_page in units:
        if current and (unit_heading != current_heading or unit_page != current_page):
            chunks.append((current, current_heading, current_page)); current = ""
        candidate = unit if not current else current + "\n\n" + unit
        if current and len(candidate) > max_chars:
            chunks.append((current, current_heading, current_page))
            # An oversized paragraph may already consume max_chars: reduce overlap
            # rather than producing an over-limit next chunk.
            overlap = current[-min(overlap_chars, max(0, max_chars - len(unit) - 2)):].strip() if overlap_chars else ""
            current = (overlap + "\n\n" if overlap else "") + unit
        else:
            current = candidate
        current_heading = unit_heading
        current_page = unit_page
    if current:
        if chunks and len(current) < min_chars and chunks[-1][1] == current_heading and chunks[-1][2] == current_page and len(chunks[-1][0]) + 2 + len(current) <= max_chars:
            chunks[-1] = (chunks[-1][0] + "\n\n" + current, current_heading, current_page)
        else:
            chunks.append((current, current_heading, current_page))
    return [Chunk(i, value, heading, page) for i, (value, heading, page) in enumerate(chunks)]