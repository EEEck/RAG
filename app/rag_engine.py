from __future__ import annotations

import json
from typing import List, Optional

from .services.search import search_lessons_and_vocab
from .services.generation import generate_items
from .schemas import GenerateItemsRequest, ConceptPack, GenerateItemsResponse

def retrieve_and_generate(book_id: str, unit: int, topic: str) -> GenerateItemsResponse:
    """
    Orchestrates the RAG pipeline:
    1. Search for content atoms based on book_id, unit, and topic.
    2. Construct a context string from the search results.
    3. Call the generation service with this context.
    """

    # 1. Search (Retrieval)
    # Returns SearchResponse object
    search_response = search_lessons_and_vocab(
        query=topic,
        top_lessons=5,
        top_vocab=5,
        max_unit=unit,
        book_id=book_id
    )

    atoms = search_response.atoms
    lessons = search_response.lessons
    vocab = search_response.vocab

    # 2. Construct Context
    # We prioritize 'atoms' which are generic.
    context_parts = []

    if atoms:
        for atom in atoms:
            context_parts.append(f"--- Segment (Score: {atom.score:.2f}) ---\n{atom.content}")
    else:
        # Fallback to legacy hits if atoms list is empty (though search.py now populates it)
        for lesson in lessons:
             if lesson.content:
                 context_parts.append(f"--- Lesson {lesson.lesson_code} ---\n{lesson.content}")
        for v in vocab:
             if v.content:
                 context_parts.append(f"--- Vocab: {v.term} ---\n{v.content}")

    full_context = "\n\n".join(context_parts)

    if not full_context:
        full_context = f"No specific content found for topic '{topic}' in Unit {unit}. Generate general items for this topic."

    # 3. Generate
    req = GenerateItemsRequest(
        textbook_id=book_id,
        lesson_code=f"Unit {unit}",
        concept_pack=ConceptPack(vocab=[], themes=[topic]),
        count=5, # Default count
        context_text=full_context
    )

    return generate_items(req)
