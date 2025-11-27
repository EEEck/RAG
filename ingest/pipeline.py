from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .docling_parser import load_docling_blocks
from .embeddings import embed_lessons, embed_vocab
from .models import LessonChunk, VocabEntry
from .segmentation import SegmentationRules, segment_lessons
from .vocab_extractor import extract_vocab_entries, link_vocab_to_lessons


def build_lessons_and_vocab(
    docling_json: str | Path,
    textbook_id: str,
    rules: SegmentationRules | None = None,
) -> Tuple[List[LessonChunk], List[VocabEntry]]:
    rules = rules or SegmentationRules()
    blocks = load_docling_blocks(docling_json)
    lessons = segment_lessons(blocks, rules, textbook_id)
    vocab = extract_vocab_entries(blocks, rules, textbook_id)
    vocab = link_vocab_to_lessons(vocab, lessons)
    return lessons, vocab


def embed_all(
    lessons: List[LessonChunk],
    vocab: List[VocabEntry],
    model: str = "text-embedding-3-large",
):
    lesson_vecs = embed_lessons(lessons, model=model)
    vocab_vecs = embed_vocab(vocab, model=model)
    return lesson_vecs, vocab_vecs
