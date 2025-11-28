from __future__ import annotations

from typing import List, Tuple

from ingest.embeddings import embed_texts

from ..db import get_conn
from ..config import get_settings
from ..schemas import LessonHit, VocabHit


def search_lessons_and_vocab(
    query: str,
    top_lessons: int = 5,
    top_vocab: int = 5,
    max_unit: int | None = None,
) -> Tuple[List[LessonHit], List[VocabHit]]:
    # TODO: Refactor this service to query the new 'content_atoms' and 'structure_nodes' tables.
    # The previous schema (lesson, vocab_entry) has been replaced.
    # Currently returning empty results to avoid SQL errors.

    return [], []
