from __future__ import annotations

from typing import Iterable, List, Sequence

from .models import LessonChunk, VocabEntry


def embed_texts(
    texts: Sequence[str],
    model: str = "text-embedding-3-large",
) -> List[List[float]]:
    """
    Embed a sequence of texts with OpenAI. Import is local to keep optional.
    """
    if not texts:
        return []
    from openai import OpenAI  # imported lazily

    client = OpenAI()
    response = client.embeddings.create(model=model, input=list(texts))
    return [item.embedding for item in response.data]


def embed_lessons(
    lessons: Iterable[LessonChunk],
    model: str = "text-embedding-3-large",
) -> List[List[float]]:
    payload = [lesson.text_for_embedding for lesson in lessons]
    return embed_texts(payload, model=model)


def embed_vocab(
    vocab_entries: Iterable[VocabEntry],
    model: str = "text-embedding-3-large",
) -> List[List[float]]:
    payload = [entry.text_for_embedding for entry in vocab_entries]
    return embed_texts(payload, model=model)
