from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


BBox = Tuple[float, float, float, float]


@dataclass
class DocBlock:
    """A single Docling text/table block with page context."""

    text: str
    page_no: int
    block_type: str = "text"
    level: Optional[int] = None
    bbox: Optional[BBox] = None
    order: int = 0

    @property
    def cleaned_text(self) -> str:
        return " ".join(self.text.split()).strip()


@dataclass
class LessonChunk:
    """Lesson-level chunk ready for embedding or DB storage."""

    textbook_id: str
    unit: Optional[int]
    lesson_code: str
    title: str
    body: str
    page_start: int
    page_end: int
    summary: Optional[str] = None

    @property
    def text_for_embedding(self) -> str:
        if self.summary:
            return self.summary
        return self.body[:1200]


@dataclass
class VocabEntry:
    """Normalized vocab entry linked to a lesson/unit where possible."""

    textbook_id: str
    term: str
    page: int
    lemma: Optional[str] = None
    pos: Optional[str] = None
    definition: Optional[str] = None
    example: Optional[str] = None
    unit: Optional[int] = None
    lesson_code: Optional[str] = None
    source: str = ""

    @property
    def text_for_embedding(self) -> str:
        parts = [self.term]
        if self.definition:
            parts.append(self.definition)
        if self.example:
            parts.append(self.example)
        return " | ".join(parts)
