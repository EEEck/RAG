from __future__ import annotations

import os
from typing import List, Tuple, Optional

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator

from ..schemas import LessonHit, VocabHit

# Singleton index to avoid reconnection churn
_VECTOR_INDEX_SINGLETON = None

def _get_vector_index() -> VectorStoreIndex:
    """Initializes and returns the singleton VectorStoreIndex backed by Postgres."""
    global _VECTOR_INDEX_SINGLETON
    if _VECTOR_INDEX_SINGLETON is not None:
        return _VECTOR_INDEX_SINGLETON

    # Setup Vector Store
    vector_store = PGVectorStore.from_params(
        database=os.getenv("POSTGRES_DB", "rag"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        password=os.getenv("POSTGRES_PASSWORD", "rag"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "rag"),
        table_name="content_atoms",
        embed_dim=1536
    )

    # Check if we should use mock embeddings (mostly for testing without API keys)
    # In production, we assume OpenAI key is present.
    if os.getenv("USE_MOCK_EMBEDDING", "False").lower() == "true":
         embed_model = MockEmbedding(embed_dim=1536)
    else:
         embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

    _VECTOR_INDEX_SINGLETON = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model
    )
    return _VECTOR_INDEX_SINGLETON

def search_lessons_and_vocab(
    query: str,
    top_lessons: int = 5,
    top_vocab: int = 5,
    max_unit: int | None = None,
    max_sequence_index: int | None = None,
) -> Tuple[List[LessonHit], List[VocabHit]]:
    """
    Searches for content atoms using LlamaIndex with optional Curriculum Guard.

    Args:
        query (str): The search query.
        top_lessons (int): Number of lesson results (not fully used in this atom-based retrieval yet).
        top_vocab (int): Number of vocab results.
        max_unit (int): Legacy filter (optional).
        max_sequence_index (int): Curriculum Guard - strict upper bound on sequence_index.
    """

    index = _get_vector_index()

    # Build Filters
    filters_list = []

    # Curriculum Guard
    if max_sequence_index is not None:
        filters_list.append(
            MetadataFilter(
                key="sequence_index",
                value=max_sequence_index,
                operator=FilterOperator.LTE
            )
        )

    # Legacy Unit Filter (if strictly required, though sequence_index is preferred)
    if max_unit is not None:
         filters_list.append(
            MetadataFilter(
                key="unit",
                value=max_unit,
                operator=FilterOperator.LTE # Assuming unit is also sequential? Or EQ?
                # Usually "max_unit" implies "up to unit X", so LTE makes sense if unit is an integer.
            )
        )

    filters = None
    if filters_list:
        filters = MetadataFilters(filters=filters_list)

    # Execute Retrieval (Single Call)
    # If filters change per request, we should instantiate retriever here.
    retriever = index.as_retriever(
        similarity_top_k=top_lessons + top_vocab,
        filters=filters
    )
    nodes = retriever.retrieve(query)

    lessons: List[LessonHit] = []
    vocab: List[VocabHit] = []

    # Map results
    # ContentAtoms are granular. We need to map them to "LessonHit" or "VocabHit"
    # This mapping is approximate since we moved to atomic storage.

    for node in nodes:
        meta = node.metadata
        score = node.score if node.score else 0.0

        # Determine if it's "vocab" or "lesson" content based on atom_type or metadata
        atom_type = meta.get("atom_type", "text")

        # Placeholder ID generation/mapping
        # In a real app, we'd look up the Lesson details from structure_nodes or similar.
        # Here we just return the atom info.

        hit_id = 0 # We don't have integer IDs for atoms readily available as primary keys here (UUIDs).
        # Schema expects int id. We might need to hash the UUID or change schema.
        # For now, using hash of node_id
        try:
             hit_id = int(hash(meta.get("node_id", "")) % 1000000)
        except:
             pass

        if atom_type == "vocab":
             vocab.append(VocabHit(
                 id=hit_id,
                 term=node.get_content().split("|")[0], # Rough extraction
                 lesson_code=str(meta.get("lesson", "")),
                 unit=int(meta.get("unit", 0)) if meta.get("unit") else None,
                 score=score
             ))
        else:
            # Default to Lesson Hit
             lessons.append(LessonHit(
                 id=hit_id,
                 lesson_code=str(meta.get("lesson", "Unknown")),
                 title=str(meta.get("title", "Content Segment")),
                 unit=int(meta.get("unit", 0)) if meta.get("unit") else None,
                 score=score
             ))

    return lessons[:top_lessons], vocab[:top_vocab]
