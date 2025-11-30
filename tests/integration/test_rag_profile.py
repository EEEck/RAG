import uuid
import pytest
from unittest.mock import MagicMock, patch
from app.services.generation import PromptFactory
from app.schemas import PedagogyConfig
from app.rag_engine import retrieve_and_generate
from app.services.profile_service import get_profile_service, ProfileService
from app.schemas import TeacherProfile

def test_prompt_factory_pedagogy_injection():
    # Test that config changes the prompt
    config = PedagogyConfig(tone="pirate", style="aggressive")
    prompt = PromptFactory.get_prompt("language", config)

    assert "Tone: pirate" in prompt
    assert "Style: aggressive" in prompt
    assert "PEDAGOGY INSTRUCTIONS" in prompt

def test_rag_flow_with_profile():
    """
    Test that providing a profile_id fetches the profile and passes config to generate_items.
    We mock the search service and generation service to focus on the orchestration logic.
    """

    # Mock Search Service
    mock_search = MagicMock()
    mock_search.search_content.return_value.atoms = [] # Empty result for simplicity

    # Mock Profile Service
    mock_profile_service = MagicMock(spec=ProfileService)
    test_profile = TeacherProfile(
        id="p123",
        user_id="u1",
        name="Test",
        pedagogy_config=PedagogyConfig(tone="humorous")
    )
    mock_profile_service.get_profile.return_value = test_profile

    # Mock Generation Service (generate_items)
    # We want to verify it receives the config
    with patch("app.rag_engine.get_search_service", return_value=mock_search), \
         patch("app.rag_engine.get_profile_service", return_value=mock_profile_service), \
         patch("app.rag_engine.generate_items") as mock_generate:

        # Call RAG engine
        retrieve_and_generate(book_id="b1", unit=1, topic="test", profile_id="p123")

        # Verify Profile Fetch
        mock_profile_service.get_profile.assert_called_with("p123")

        # Verify Generation Call
        args, kwargs = mock_generate.call_args
        assert kwargs['pedagogy_config'] is not None
        assert kwargs['pedagogy_config'].tone == "humorous"

def test_rag_flow_without_profile():
    with patch("app.rag_engine.get_search_service") as mock_search, \
         patch("app.rag_engine.get_profile_service") as mock_ps, \
         patch("app.rag_engine.generate_items") as mock_generate:

        mock_search.return_value.search_content.return_value.atoms = []

        retrieve_and_generate(book_id="b1", unit=1, topic="test", profile_id=None)

        mock_ps.assert_not_called()
        args, kwargs = mock_generate.call_args
        assert kwargs['pedagogy_config'] is None
