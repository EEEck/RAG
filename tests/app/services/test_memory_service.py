import pytest
from unittest.mock import MagicMock, patch
from app.services.memory_service import MemoryService
from app.models.artifact import Artifact
from app.schemas import AtomHit

@pytest.fixture
def mock_repo():
    return MagicMock()

@pytest.fixture
def mock_openai():
    with patch("app.services.memory_service.OpenAI") as mock:
        mock_instance = mock.return_value
        # Mock embeddings response
        mock_instance.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        yield mock_instance

@pytest.fixture
def mock_settings():
    with patch("app.services.memory_service.get_settings") as mock:
        mock.return_value.openai_api_key = "test_key"
        yield mock

def test_save_artifact(mock_repo, mock_openai, mock_settings):
    service = MemoryService(repo=mock_repo)

    artifact = service.save_artifact(
        profile_id="teacher_1",
        content="This is a test lesson",
        artifact_type="lesson",
        topic_tags=["grammar"]
    )

    assert artifact.profile_id == "teacher_1"
    assert artifact.content == "This is a test lesson"
    assert artifact.type == "lesson"
    assert artifact.embedding == [0.1, 0.2, 0.3]

    mock_repo.save_artifact.assert_called_once()

def test_search_artifacts(mock_repo, mock_openai, mock_settings):
    service = MemoryService(repo=mock_repo)

    # Mock repo return
    mock_artifact = Artifact(
        profile_id="teacher_1",
        type="quiz",
        content="Quiz Content",
        related_book_ids=["book1"]
    )
    mock_repo.search_artifacts.return_value = [mock_artifact]

    hits = service.search_artifacts("teacher_1", query="test")

    assert len(hits) == 1
    assert isinstance(hits[0], AtomHit)
    # AtomHit has metadata dict
    assert hits[0].metadata["content_type"] == "quiz"
    assert hits[0].metadata["profile_id"] == "teacher_1"
    assert hits[0].score == 1.0
