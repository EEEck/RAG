from __future__ import annotations

from typing import List, Tuple

from ingest.embeddings import embed_texts

from ..config import get_settings
from ..db import get_conn
from ..schemas import ConceptPack, ConceptPackRequest, ConceptPackResponse


def build_concept_pack(req: ConceptPackRequest) -> ConceptPackResponse:
    """
    Build a simple concept pack from lessons + vocab for a given textbook/lesson.
    """
    settings = get_settings()

    with get_conn() as conn, conn.cursor() as cur:
        # Anchor lesson
        cur.execute(
            """
            SELECT id, unit, lesson_code, title, COALESCE(details_md, '') AS body
            FROM lesson
            WHERE textbook_id = %s AND lesson_code = %s
            ORDER BY id
            LIMIT 1
            """,
            (req.textbook_id, req.lesson_code),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("Anchor lesson not found")
        anchor_id, anchor_unit, anchor_code, anchor_title, anchor_body = row

        # Allowed scope: prior units including anchor
        cur.execute(
            """
            SELECT id, unit, lesson_code, title
            FROM lesson
            WHERE textbook_id = %s
              AND (unit IS NULL OR unit <= %s)
            ORDER BY unit NULLS FIRST, lesson_code
            """,
            (req.textbook_id, anchor_unit if anchor_unit is not None else 10**6),
        )
        scope_lessons = cur.fetchall()
        scope_ids = [r[0] for r in scope_lessons]

        # Query embedding based on request_text or anchor text
        query_text = (
            req.request_text
            or f"{anchor_title}\n{anchor_body[:400]}"
        )
        emb = embed_texts([query_text], model=settings.embed_model)[0]

        # Top-K lesson neighbors within scope
        cur.execute(
            """
            SELECT id, unit, lesson_code, title
            FROM lesson
            WHERE id = ANY(%s)
            ORDER BY emb <-> %s
            LIMIT %s
            """,
            (scope_ids, emb, req.k_lessons),
        )
        neighbor_lessons = cur.fetchall()

        # Vocab across scoped lessons (prior units)
        cur.execute(
            """
            SELECT term
            FROM vocab_entry
            WHERE textbook_id = %s
              AND (unit IS NULL OR unit <= %s)
            LIMIT %s
            """,
            (req.textbook_id, anchor_unit if anchor_unit is not None else 10**6, req.k_vocab * 5),
        )
        vocab_terms = [r[0] for r in cur.fetchall()]

    vocab_unique: List[str] = sorted({t.strip() for t in vocab_terms if t and t.strip()})

    concept = ConceptPack(
        vocab=vocab_unique[: req.k_vocab],
        grammar_rules=[],
        themes=[],
    )

    return ConceptPackResponse(
        anchor_lesson_id=anchor_id,
        allowed_scope_count=len(scope_ids),
        concept_pack=concept,
    )

