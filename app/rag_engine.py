from __future__ import annotations

import json
from typing import List, Optional

from .services.search_service import get_search_service
from .services.generation import generate_items
from .services.memory_service import MemoryService
from .services.profile_service import get_profile_service
from .schemas import GenerateItemsRequest, ConceptPack, GenerateItemsResponse, PedagogyConfig

def retrieve_and_generate(
    
    book_id: str,
   
    unit: int,
   
    topic: str,
   
    category: str = "language",
    profile_id: Optional[str] = None
,
    profile_id: Optional[str] = None,
    use_memory: bool = False
) -> GenerateItemsResponse:
    """
    Orchestrates the RAG pipeline:
    1. Search for content atoms based on book_id, unit, and topic.
    2. Optional: Search for memory artifacts if profile_id is provided.
    3. Construct a context string from the search results.
    4. Call the generation service with this context.
    """

    # 0. Fetch Profile Context (if profile_id provided)
    pedagogy_config = None
    if profile_id:
        profile_service = get_profile_service()
        profile = profile_service.get_profile(profile_id)
        if profile:
            pedagogy_config = profile.pedagogy_config

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

    atoms = search_response.atoms if search_response.atoms else []

    # 2. Memory Retrieval (Feature 3)
    memory_hits = []
    if use_memory and profile_id:
        print(f"Retrieving memory artifacts for profile {profile_id}...")
        try:
            memory_service = MemoryService() # Instantiate or inject
            memory_hits = memory_service.search_artifacts(profile_id, query=topic, limit=3)
        except Exception as e:
            print(f"Warning: Memory retrieval failed: {e}")

    # 3. Construct Context
    context_parts = []

    # Add Textbook Content
    if atoms:
        context_parts.append("### Textbook Content ###")
        for atom in atoms:
            context_parts.append(f"--- Segment (Type: {atom.metadata.get('atom_type', 'text')}) ---\n{atom.content}")

    # Add Memory Content
    if memory_hits:
        context_parts.append("\n### Previous Class Memory (Do not repeat exact questions, but build upon them) ###")
        for hit in memory_hits:
            context_parts.append(hit.content)

    full_context = "\n\n".join(context_parts)

    if not full_context:
        full_context = f"No specific content found for topic '{topic}' in Unit {unit}. Generate general items for this topic."

    # 4. Generate
    req = GenerateItemsRequest(
        textbook_id=book_id,
        lesson_code=f"Unit {unit}",
        concept_pack=ConceptPack(vocab=[], themes=[topic]),
        count=5, # Default count
        context_text=full_context,
        category=category,
        profile_id=profile_id,
        use_memory=use_memory
    )

    return generate_items(req, pedagogy_config=pedagogy_config)
