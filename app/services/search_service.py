from __future__ import annotations

import os
from typing import List, Optional

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator

from ..schemas import LessonHit, VocabHit, AtomHit, SearchResponse

class SearchService:
    """
    Encapsulates logic for searching content atoms using LlamaIndex.
    Uses Dependency Injection for the VectorStoreIndex.
    """

    def __init__(self, index: VectorStoreIndex):
        self.index = index

    def search_content(
        self,
        query: str,
        limit: int = 10,
        max_unit: int | None = None,
        max_sequence_index: int | None = None,
        book_id: str | None = None,
    ) -> SearchResponse:
        """
        Searches for content atoms using LlamaIndex with optional Curriculum Guard.
        Returns generic AtomHit objects.
        """

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

        # Legacy Unit Filter (Generalized to work for any domain using 'unit')
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

        # Execute Retrieval
        retriever = self.index.as_retriever(
            similarity_top_k=limit,
            filters=filters
        )
        nodes = retriever.retrieve(query)

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

        return SearchResponse(
            lessons=[], # Legacy support: return empty
            vocab=[],   # Legacy support: return empty
            atoms=atoms
        )

def get_search_service() -> SearchService:
    """Factory to create the default SearchService with Postgres."""

    # Default to Postgres
    vector_store = PGVectorStore.from_params(
        database=os.getenv("POSTGRES_DB", "rag"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        password=os.getenv("POSTGRES_PASSWORD", "rag"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "rag"),
        table_name="content_atoms",
        embed_dim=1536
    )

    # Check if we should use mock embeddings
    if os.getenv("USE_MOCK_EMBEDDING", "False").lower() == "true":
         embed_model = MockEmbedding(embed_dim=1536)
    else:
         embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model
    )

    return SearchService(index)
