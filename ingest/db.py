from __future__ import annotations

from typing import Iterable, Sequence

from .models import LessonChunk, VocabEntry


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS textbook (
  id           TEXT PRIMARY KEY,
  brand        TEXT,
  edition      TEXT,
  locale       TEXT,
  grade_from   INT,
  grade_to     INT
);

CREATE TABLE IF NOT EXISTS lesson (
  id           BIGSERIAL PRIMARY KEY,
  textbook_id  TEXT REFERENCES textbook(id),
  unit         INT,
  lesson_code  TEXT,
  title        TEXT,
  summary_json JSONB,
  details_md   TEXT,
  page_start   INT,
  page_end     INT,
  emb          VECTOR(1536),
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vocab_entry (
  id           BIGSERIAL PRIMARY KEY,
  textbook_id  TEXT REFERENCES textbook(id),
  unit         INT,
  lesson_code  TEXT,
  term         TEXT,
  lemma        TEXT,
  pos          TEXT,
  definition   TEXT,
  example      TEXT,
  page         INT,
  emb          VECTOR(1536),
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lesson_textbook_idx ON lesson(textbook_id, unit, lesson_code);
CREATE INDEX IF NOT EXISTS vocab_textbook_idx ON vocab_entry(textbook_id, unit, lesson_code);
CREATE INDEX IF NOT EXISTS lesson_emb_hnsw ON lesson USING hnsw (emb vector_cosine_ops);
CREATE INDEX IF NOT EXISTS vocab_emb_hnsw ON vocab_entry USING hnsw (emb vector_cosine_ops);
"""


def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()


def insert_lessons(conn, lessons: Iterable[LessonChunk], embeddings: Sequence[Sequence[float]] | None = None) -> None:
    data = list(lessons)
    cur = conn.cursor()
    for idx, lesson in enumerate(data):
        emb = embeddings[idx] if embeddings is not None else None
        cur.execute(
            """
            INSERT INTO lesson (textbook_id, unit, lesson_code, title, summary_json, details_md, page_start, page_end, emb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                lesson.textbook_id,
                lesson.unit,
                lesson.lesson_code,
                lesson.title,
                None,
                lesson.body,
                lesson.page_start,
                lesson.page_end,
                emb,
            ),
        )
    conn.commit()


def insert_vocab(conn, vocab: Iterable[VocabEntry], embeddings: Sequence[Sequence[float]] | None = None) -> None:
    data = list(vocab)
    cur = conn.cursor()
    for idx, entry in enumerate(data):
        emb = embeddings[idx] if embeddings is not None else None
        cur.execute(
            """
            INSERT INTO vocab_entry (textbook_id, unit, lesson_code, term, lemma, pos, definition, example, page, emb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry.textbook_id,
                entry.unit,
                entry.lesson_code,
                entry.term,
                entry.lemma,
                entry.pos,
                entry.definition,
                entry.example,
                entry.page,
                emb,
            ),
        )
    conn.commit()
