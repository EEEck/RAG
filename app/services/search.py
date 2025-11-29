from __future__ import annotations

import os
from typing import List, Tuple, Optional, Any, Dict

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator

from ..schemas import LessonHit, VocabHit, AtomHit, SearchResponse

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
    book_id: str | None = None,
) -> SearchResponse:
    """
    Searches for content atoms using LlamaIndex with optional Curriculum Guard.
    Returns a SearchResponse object containing lessons, vocab, and generic atoms.
    """

    index = _get_vector_index()

    # Build Filters
    filters_list = []

    if book_id:
        filters_list.append(
            MetadataFilter(
                key="book_id",
                value=book_id,
                operator=FilterOperator.EQ
            )
        )

    # Curriculum Guard
    if max_sequence_index is not None:
        filters_list.append(
            MetadataFilter(
                key="sequence_index",
                value=max_sequence_index,
                operator=FilterOperator.LTE
            )
        )

    # Legacy Unit Filter
    if max_unit is not None:
         filters_list.append(
            MetadataFilter(
                key="unit",
                value=max_unit,
                operator=FilterOperator.LTE
            )
        )

    filters = None
    if filters_list:
        filters = MetadataFilters(filters=filters_list)

    # Execute Retrieval (Single Call)
    retriever = index.as_retriever(
        similarity_top_k=top_lessons + top_vocab,
        filters=filters
    )
    nodes = retriever.retrieve(query)

    lessons: List[LessonHit] = []
    vocab: List[VocabHit] = []
    atoms: List[AtomHit] = []

    # Map results
    for node in nodes:
        meta = node.metadata
        score = node.score if node.score else 0.0
        content = node.get_content()

        # Generic Atom Hit
        atom_hit = AtomHit(
            id=str(node.node_id),
            content=content,
            metadata=meta,
            score=score
        )
        atoms.append(atom_hit)

        # Legacy Mapping for specific ESL use-cases (if needed by frontend)
        atom_type = meta.get("atom_type", "text")

        hit_id = 0
        try:
             hit_id = int(hash(meta.get("node_id", str(node.node_id))) % 1000000)
        except:
             pass

        if atom_type == "vocab":
             vocab.append(VocabHit(
                 id=hit_id,
                 term=content.split("|")[0],
                 lesson_code=str(meta.get("lesson", "")),
                 unit=int(meta.get("unit", 0)) if meta.get("unit") else None,
                 score=score,
                 content=content
             ))
        else:
             lessons.append(LessonHit(
                 id=hit_id,
                 lesson_code=str(meta.get("lesson", "Unknown")),
                 title=str(meta.get("title", "Content Segment")),
                 unit=int(meta.get("unit", 0)) if meta.get("unit") else None,
                 score=score,
                 content=content
             ))

    return SearchResponse(
        lessons=lessons[:top_lessons],
        vocab=vocab[:top_vocab],
        atoms=atoms
    )
