from __future__ import annotations

import os
from typing import List, Optional

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator, FilterCondition

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
        book_ids: List[str] | None = None,
        user_id: str | None = None,
    ) -> SearchResponse:
        """
        Searches for content atoms using LlamaIndex with optional Curriculum Guard and Privacy Filters.
        Returns generic AtomHit objects.

        Args:
            query (str): The search query.
            limit (int): Max number of results.
            max_unit (int | None): (Legacy) Limit results to unit <= max_unit.
            max_sequence_index (int | None): Strict curriculum guard. Limit results to sequence_index <= max.
            book_ids (List[str] | None): Restrict search to specific book IDs.
            user_id (str | None): The ID of the requesting user. Used to enforce privacy (User Content + Global).
        """

        # Build Filters
        filters_list = []

        # Privacy Filter
        if user_id:
            # Match User OR Global (missing owner_id)
            filters_list.append(
                MetadataFilters(
                    filters=[
                        MetadataFilter(key="owner_id", value=user_id, operator=FilterOperator.EQ),
                        MetadataFilter(key="owner_id", value=None, operator=FilterOperator.IS_EMPTY),
                    ],
                    condition=FilterCondition.OR
                )
            )
        else:
            # Global only (missing owner_id)
            filters_list.append(
                MetadataFilter(key="owner_id", value=None, operator=FilterOperator.IS_EMPTY)
            )

        if book_ids:
            if len(book_ids) == 1:
                filters_list.append(
                    MetadataFilter(
                        key="book_id",
                        value=book_ids[0],
                        operator=FilterOperator.EQ
                    )
                )
            else:
                filters_list.append(
                    MetadataFilter(
                        key="book_id",
                        value=book_ids,
                        operator=FilterOperator.IN
                    )
                )
        elif book_ids is not None and len(book_ids) == 0:
            # If book_ids is explicitly empty (e.g. strict mode with no books), return empty results
            return SearchResponse(
                lessons=[],
                vocab=[],
                atoms=[]
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
