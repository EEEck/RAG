from __future__ import annotations

import json
from typing import List, Optional

from .services.search_service import get_search_service
from .services.generation import generate_items
from .services.profile_service import get_profile_service
from .schemas import GenerateItemsRequest, ConceptPack, GenerateItemsResponse, PedagogyConfig

def retrieve_and_generate(
    book_id: str,
    unit: int,
    topic: str,
    category: str = "language",
    profile_id: Optional[str] = None
) -> GenerateItemsResponse:
    """
    Orchestrates the RAG pipeline:
    1. Search for content atoms based on book_id, unit, and topic.
    2. Construct a context string from the search results.
    3. Call the generation service with this context.
    """

    # 0. Fetch Profile Context (if profile_id provided)
    pedagogy_config = None
    if profile_id:
        profile_service = get_profile_service()
        profile = profile_service.get_profile(profile_id)
        if profile:
            pedagogy_config = profile.pedagogy_config

    # 1. Search (Retrieval)
    search_service = get_search_service()

    # Returns SearchResponse object with generic atoms
    search_response = search_service.search_content(
        query=topic,
        limit=10, # Combine previous top_lessons + top_vocab
        max_unit=unit,
        book_id=book_id
    )

    atoms = search_response.atoms

    # 2. Construct Context
    context_parts = []

    if atoms:
        for atom in atoms:
            # We can optionally differentiate display based on metadata type
            # but for the LLM context, raw content is usually best.
            context_parts.append(f"--- Segment (Type: {atom.metadata.get('atom_type', 'text')}) ---\n{atom.content}")

    full_context = "\n\n".join(context_parts)

    if not full_context:
        full_context = f"No specific content found for topic '{topic}' in Unit {unit}. Generate general items for this topic."

    # 3. Generate
    req = GenerateItemsRequest(
        textbook_id=book_id,
        lesson_code=f"Unit {unit}",
        concept_pack=ConceptPack(vocab=[], themes=[topic]),
        count=5, # Default count
        context_text=full_context,
        category=category # Pass the category to select the correct prompt
    )

    return generate_items(req, pedagogy_config=pedagogy_config)
