import pytest
from unittest.mock import MagicMock, patch
from app.rag_engine import retrieve_and_generate
from app.schemas import GenerateItemsResponse, SearchResponse, AtomHit, TeacherProfile, PedagogyConfig, ScopeReport, ConceptPack

@patch("app.rag_engine.get_search_service")
@patch("app.rag_engine.get_profile_service")
@patch("app.rag_engine.MemoryService")
@patch("app.rag_engine.generate_items")
def test_retrieve_and_generate(mock_generate, mock_memory_cls, mock_get_profile, mock_get_search):
    # Setup Mocks
    mock_search_service = MagicMock()
    mock_get_search.return_value = mock_search_service

    mock_profile_service = MagicMock()
    mock_get_profile.return_value = mock_profile_service

    mock_memory_service = MagicMock()
    mock_memory_cls.return_value = mock_memory_service

    # Mock Search Response
    atom = AtomHit(
        id="atom1",
        content="This is content",
        metadata={"atom_type": "text"},
        score=0.9
    )
    mock_search_service.search_content.return_value = SearchResponse(
        lessons=[], vocab=[], atoms=[atom]
    )

    # Mock Memory Response
    memory_hit = MagicMock()
    memory_hit.content = "Memory content"
    mock_memory_service.search_artifacts.return_value = [memory_hit]

    # Mock Profile Response
    mock_profile = TeacherProfile(
        user_id="u1", name="T1",
        pedagogy_config=PedagogyConfig(tone="strict")
    )
    mock_profile_service.get_profile.return_value = mock_profile

    # Mock Generate Response
    mock_generate.return_value = GenerateItemsResponse(
        items=[],
        scope_report=ScopeReport(violations=0)
    )

    # Run
    retrieve_and_generate(
        book_id="book1",
        unit=1,
        topic="topic",
        profile_id="p1",
        use_memory=True
    )

    # Verify Calls
    mock_get_profile.assert_called_once()
    mock_profile_service.get_profile.assert_called_with("p1")

    mock_get_search.assert_called_once()
    mock_search_service.search_content.assert_called()

    mock_memory_cls.assert_called_once()
    mock_memory_service.search_artifacts.assert_called_with("p1", query="topic", limit=3)

    mock_generate.assert_called_once()
    args, kwargs = mock_generate.call_args
    req = args[0]
    assert "This is content" in req.context_text
    assert "Memory content" in req.context_text
    assert kwargs["pedagogy_config"] == mock_profile.pedagogy_config
