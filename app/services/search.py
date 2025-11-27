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
    settings = get_settings()
    emb = embed_texts([query], model=settings.embed_model)[0]

    lessons: List[LessonHit] = []
    vocab_hits: List[VocabHit] = []

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, unit, lesson_code, title, (emb <-> %s) AS score
                FROM lesson
                WHERE (%s IS NULL OR unit <= %s)
                ORDER BY score ASC
                LIMIT %s
                """,
                (emb, max_unit, max_unit, top_lessons),
            )
            for row in cur.fetchall():
                lessons.append(
                    LessonHit(
                        id=row[0],
                        unit=row[1],
                        lesson_code=row[2],
                        title=row[3],
                        score=float(row[4]),
                    )
                )

            cur.execute(
                """
                SELECT id, unit, lesson_code, term, (emb <-> %s) AS score
                FROM vocab_entry
                WHERE (%s IS NULL OR unit <= %s)
                ORDER BY score ASC
                LIMIT %s
                """,
                (emb, max_unit, max_unit, top_vocab),
            )
            for row in cur.fetchall():
                vocab_hits.append(
                    VocabHit(
                        id=row[0],
                        unit=row[1],
                        lesson_code=row[2],
                        term=row[3],
                        score=float(row[4]),
                    )
                )

    return lessons, vocab_hits
