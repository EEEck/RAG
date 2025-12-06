import uuid
import pytest
from unittest.mock import MagicMock
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator, FilterCondition

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
    # Expect default owner_id is empty filter
    call_args = index.as_retriever.call_args
    assert call_args is not None
    kwargs = call_args.kwargs

    assert kwargs["similarity_top_k"] == 10
    filters = kwargs["filters"]
    assert isinstance(filters, MetadataFilters)
    assert len(filters.filters) == 1
    f = filters.filters[0]
    assert f.key == "owner_id"
    assert f.operator == FilterOperator.IS_EMPTY

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
        book_ids=["book-123"],
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
    # We expect owner_id, book_id, unit, sequence_index -> 4 filters
    assert len(filters.filters) == 4

    # Verify individual filters
    # Note: filters.filters is a list
    f_owner = next(f for f in filters.filters if f.key == "owner_id")
    assert f_owner.operator == FilterOperator.IS_EMPTY

    f_book = next(f for f in filters.filters if f.key == "book_id")
    assert f_book.value == "book-123"
    assert f_book.operator == FilterOperator.EQ

    f_unit = next(f for f in filters.filters if f.key == "unit")
    assert f_unit.value == 3
    assert f_unit.operator == FilterOperator.LTE

    f_seq = next(f for f in filters.filters if f.key == "sequence_index")
    assert f_seq.value == 10
    assert f_seq.operator == FilterOperator.LTE

def test_search_content_with_user_id(mock_index):
    index, retriever = mock_index
    service = SearchService(index)

    service.search_content("query", user_id="user-1")

    call_args = index.as_retriever.call_args
    filters = call_args.kwargs["filters"]

    # Expect 1 item in top level filters list which is the OR group (nested MetadataFilters)
    assert len(filters.filters) == 1
    or_group = filters.filters[0]

    assert isinstance(or_group, MetadataFilters)
    assert or_group.condition == FilterCondition.OR
    assert len(or_group.filters) == 2

    f1 = or_group.filters[0]
    f2 = or_group.filters[1]

    # Check that one matches user-1 and other is empty
    values = {f.value for f in or_group.filters}
    assert "user-1" in values
    assert None in values
