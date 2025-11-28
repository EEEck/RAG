from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List


BBox = Tuple[float, float, float, float]


@dataclass
class StructureNode:
    """
    Represents a hierarchical node in the document structure (e.g., Unit, Chapter, Section).

    Attributes:
        id (uuid.UUID): Unique identifier for the node.
        book_id (uuid.UUID): Foreign key to the Book.
        parent_id (Optional[uuid.UUID]): Pointer to the parent StructureNode.
        node_level (int): Depth level (0=Root, 1=Chapter, etc.).
        title (str): Title or heading of the section.
        sequence_index (int): Ordering index within the parent/book.
        meta_data (Dict[str, Any]): Additional metadata (page numbers, providers, etc.).
    """
    id: uuid.UUID
    book_id: uuid.UUID
    parent_id: Optional[uuid.UUID]
    node_level: int
    title: str
    sequence_index: int
    meta_data: Dict[str, Any]


@dataclass
class ContentAtom:
    """
    Represents a granular piece of content (text, image description) belonging to a node.

    Attributes:
        id (uuid.UUID): Unique identifier for the atom.
        book_id (uuid.UUID): Foreign key to the Book.
        node_id (Optional[uuid.UUID]): Foreign key to the parent StructureNode.
        atom_type (str): Type of content (e.g., 'text', 'image', 'table').
        content_text (str): The actual text content.
        meta_data (Dict[str, Any]): Additional metadata (layout info, providence).
        embedding (Optional[List[float]]): Vector embedding of the content.
    """
    id: uuid.UUID
    book_id: uuid.UUID
    node_id: Optional[uuid.UUID]
    atom_type: str
    content_text: str
    meta_data: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class DocBlock:
    """
    A single Docling text/table block with page context.

    Attributes:
        text (str): Raw text content.
        page_no (int): Page number where this block appears.
        block_type (str): Type classification (default 'text').
        level (Optional[int]): Heading level if applicable.
        bbox (Optional[BBox]): Bounding box coordinates (x0, y0, x1, y1).
        order (int): Reading order index.
    """

    text: str
    page_no: int
    block_type: str = "text"
    level: Optional[int] = None
    bbox: Optional[BBox] = None
    order: int = 0

    @property
    def cleaned_text(self) -> str:
        """Returns whitespace-normalized text."""
        return " ".join(self.text.split()).strip()


@dataclass
class LessonChunk:
    """
    Lesson-level chunk ready for embedding or DB storage.

    Attributes:
        textbook_id (str): Identifier of the textbook.
        unit (Optional[int]): Unit number.
        lesson_code (str): Short code for the lesson.
        title (str): Lesson title.
        body (str): Full text of the lesson chunk.
        page_start (int): Starting page number.
        page_end (int): Ending page number.
        summary (Optional[str]): Optional summary of the lesson.
    """

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
        """Returns text suitable for embedding generation (summary preferred)."""
        if self.summary:
            return self.summary
        return self.body[:1200]


@dataclass
class VocabEntry:
    """
    Normalized vocab entry linked to a lesson/unit where possible.

    Attributes:
        textbook_id (str): Identifier of the textbook.
        term (str): The vocabulary term.
        page (int): Page number where it appears.
        lemma (Optional[str]): Base form of the word.
        pos (Optional[str]): Part of speech.
        definition (Optional[str]): Definition text.
        example (Optional[str]): Example usage sentence.
        unit (Optional[int]): Unit number.
        lesson_code (Optional[str]): Lesson code.
        source (str): Source identifier.
    """

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
        """Concatenates term, definition, and example for embedding."""
        parts = [self.term]
        if self.definition:
            parts.append(self.definition)
        if self.example:
            parts.append(self.example)
        return " | ".join(parts)
