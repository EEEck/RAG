import pytest
import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.memory_service import MemoryService
from app.models.artifact import Artifact

@pytest.fixture
def mock_repo():
    return MagicMock()

@pytest.fixture
def mock_openai():
    with patch("app.services.memory_service.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client

@pytest.fixture
def service(mock_repo, mock_openai):
    return MemoryService(repo=mock_repo)

def test_save_artifact(service, mock_repo, mock_openai):
    # Setup mock embedding
    mock_openai.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2])]

    # Run
    art = service.save_artifact("p1", "content", summary="summary")

    assert art.profile_id == "p1"
    assert art.embedding == [0.1, 0.2]
    mock_repo.save_artifact.assert_called_once()

def test_search_artifacts(service, mock_repo, mock_openai):
    mock_openai.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2])]

    mock_art = Artifact(id=uuid.uuid4(), profile_id="p1", content="content", created_at=datetime.utcnow(), type="quiz")
    mock_repo.search_artifacts.return_value = [mock_art]

    hits = service.search_artifacts("p1", "query")

    assert len(hits) == 1
    assert "PREVIOUS CLASS MEMORY" in hits[0].content
    mock_repo.search_artifacts.assert_called_once()

def test_get_artifacts_in_range(service, mock_repo):
    service.get_artifacts_in_range("p1", datetime.utcnow(), datetime.utcnow())
    mock_repo.get_artifacts_by_date_range.assert_called_once()
