import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.review_service import ReviewService
from app.models.artifact import Artifact
from app.schemas import GenerateItemsResponse, SearchResponse, AtomHit

@pytest.fixture
def mock_memory_service():
    return MagicMock()

@pytest.fixture
def mock_search_service():
    return MagicMock()

@pytest.fixture
def review_service(mock_memory_service, mock_search_service):
    return ReviewService(memory_service=mock_memory_service, search_service=mock_search_service)

def test_generate_review_quiz_flow(review_service, mock_memory_service, mock_search_service):
    # Setup Mocks
    profile_id = "test-profile"

    # 1. Mock Artifacts
    import uuid
    mock_artifact = Artifact(
        id=uuid.uuid4(),
        profile_id=profile_id,
        type="lesson",
        content="Past lesson content",
        summary="Summary of past lesson",
        created_at=datetime.utcnow() - timedelta(days=2),
        topic_tags=["grammar", "past_tense"]
    )
    mock_memory_service.get_artifacts_in_range.return_value = [mock_artifact]

    # 2. Mock Search
    mock_atom = AtomHit(id="1", content="Textbook content about past tense", metadata={}, score=0.9)
    mock_search_service.search_content.return_value = SearchResponse(atoms=[mock_atom], lessons=[], vocab=[])

    # 3. Mock Generation (patching the function imported in review_service)
    from app.schemas import ScopeReport
    with patch("app.services.review_service.generate_items") as mock_generate:
        mock_generate.return_value = GenerateItemsResponse(items=[], scope_report=ScopeReport(violations=0, notes=[]))

        # 4. Mock Profile Service (fetched inside the method)
        with patch("app.services.review_service.get_profile_service") as mock_get_profile_service:
            mock_profile_service = MagicMock()
            mock_profile_service.get_profile.return_value = MagicMock(pedagogy_config=None)
            mock_get_profile_service.return_value = mock_profile_service

            # Execute
            response = review_service.generate_review_quiz(profile_id, time_window="last_7_days")

            # Assertions

            # Check Memory Service call
            mock_memory_service.get_artifacts_in_range.assert_called_once()
            args, _ = mock_memory_service.get_artifacts_in_range.call_args
            assert args[0] == profile_id
            # Assert date range is approx correct (difficult to match exact microsecond, but we check calls happened)

            # Check Search Service call
            mock_search_service.search_content.assert_called_once()
            # Should search for topics found in artifact
            call_kwargs = mock_search_service.search_content.call_args[1]
            assert "grammar" in call_kwargs['query'] or "past_tense" in call_kwargs['query']

            # Check Generate call
            mock_generate.assert_called_once()
            gen_req = mock_generate.call_args[0][0]
            assert "Summary of past lesson" in gen_req.context_text
            assert "Textbook content about past tense" in gen_req.context_text
            assert "grammar" in gen_req.concept_pack.themes or "past_tense" in gen_req.concept_pack.themes

def test_generate_review_no_artifacts(review_service, mock_memory_service):
    # Setup: No artifacts returned
    mock_memory_service.get_artifacts_in_range.return_value = []

    response = review_service.generate_review_quiz("test-profile")

    # Should return empty response or handle gracefully
    assert len(response.items) == 0
