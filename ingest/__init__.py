"""Backend helpers for Docling-based ESL textbook ingestion."""

from .models import DocBlock, LessonChunk, VocabEntry
from .docling_parser import load_docling_blocks
from .segmentation import SegmentationRules, segment_lessons
from .vocab_extractor import extract_vocab_entries, link_vocab_to_lessons
from .pipeline import build_lessons_and_vocab, embed_all

__all__ = [
    "DocBlock",
    "LessonChunk",
    "VocabEntry",
    "SegmentationRules",
    "segment_lessons",
    "load_docling_blocks",
    "extract_vocab_entries",
    "link_vocab_to_lessons",
    "build_lessons_and_vocab",
    "embed_all",
]
