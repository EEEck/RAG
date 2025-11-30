import uuid
import pytest
from unittest.mock import MagicMock
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator

from app.services.search_service import SearchService
from app.schemas import SearchResponse

@pytest.fixture
def mock_index():
    index = MagicMock()
    retriever = MagicMock()
    index.as_retriever.return_value = retriever
    return index, retriever

def test_search_content_basic(mock_index):
    index, retriever = mock_index
    service = SearchService(index)

    # Setup mock return
    node = TextNode(
        text="Sample content",
        metadata={"unit": 1, "category": "math"},
        node_id=str(uuid.uuid4())
    )
    retriever.retrieve.return_value = [NodeWithScore(node=node, score=0.85)]

    response = service.search_content("query")

    # Check Retriever call
    index.as_retriever.assert_called_with(similarity_top_k=10, filters=None)
    retriever.retrieve.assert_called_with("query")

    # Check Response
    assert len(response.atoms) == 1
    assert response.atoms[0].content == "Sample content"
    assert response.atoms[0].score == 0.85
    assert response.atoms[0].metadata["unit"] == 1

def test_search_content_with_filters(mock_index):
    index, retriever = mock_index
    service = SearchService(index)

    service.search_content(
        "query",
        limit=5,
        book_id="book-123",
        max_unit=3,
        max_sequence_index=10
    )

    # Verify filters
    call_args = index.as_retriever.call_args
    assert call_args is not None
    kwargs = call_args.kwargs

    assert kwargs["similarity_top_k"] == 5
    filters = kwargs["filters"]
    assert isinstance(filters, MetadataFilters)
    assert len(filters.filters) == 3

    # Verify individual filters
    # Note: filters.filters is a list
    f_book = next(f for f in filters.filters if f.key == "book_id")
    assert f_book.value == "book-123"
    assert f_book.operator == FilterOperator.EQ

    f_unit = next(f for f in filters.filters if f.key == "unit")
    assert f_unit.value == 3
    assert f_unit.operator == FilterOperator.LTE

    f_seq = next(f for f in filters.filters if f.key == "sequence_index")
    assert f_seq.value == 10
    assert f_seq.operator == FilterOperator.LTE
