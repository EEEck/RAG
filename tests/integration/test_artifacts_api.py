from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.main import app
from app.models.artifact import Artifact
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService, get_profile_service
from app.routes.artifacts import get_memory_service
import uuid

# Helper to create mock artifacts
def create_mock_artifact(id_val, profile_id, type_val, created_at, summary):
    return Artifact(
        id=uuid.UUID(id_val),
        profile_id=profile_id,
        type=type_val,
        content="some content",
        summary=summary,
        created_at=created_at,
        embedding=None,
        related_book_ids=[],
        topic_tags=[]
    )

def test_get_timeline_success():
    """
    Test GET /artifacts/timeline with valid parameters.
    """
    # 1. Setup Mocks
    mock_profile_service = MagicMock(spec=ProfileService)
    mock_memory_service = MagicMock(spec=MemoryService)

    # Mock Data
    profile_id = "test_profile_1"
    mock_profile_service.get_profile.return_value = True # Profile exists

    # Mock artifacts returned by service
    art1 = create_mock_artifact(
        "12345678-1234-5678-1234-567812345678",
        profile_id,
        "lesson",
        datetime(2023, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
        "Lesson on Photosynthesis"
    )
    art2 = create_mock_artifact(
        "87654321-4321-8765-4321-876543210987",
        profile_id,
        "quiz",
        datetime(2023, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
        "Quiz on Biology"
    )

    # Return specific list
    mock_memory_service.get_artifacts_in_range.return_value = [art2, art1]

    # 2. Override Dependencies
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_memory_service] = lambda: mock_memory_service

    client = TestClient(app)

    try:
        # 3. Make Request
        params = {
            "profile_id": profile_id,
            "start_date": "2023-10-01T00:00:00Z",
            "end_date": "2023-10-31T23:59:59Z",
            "type": "lesson"
        }

        response = client.get("/artifacts/timeline", params=params)

        # 4. Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Check first item (most recent)
        assert data[0]["id"] == str(art2.id)
        assert data[0]["type"] == "quiz"
        assert data[0]["title"] == "Quiz on Biology"
        assert data[0]["date"] == art2.created_at.isoformat()

        # Verify service call
        mock_memory_service.get_artifacts_in_range.assert_called_once()
        call_kwargs = mock_memory_service.get_artifacts_in_range.call_args.kwargs
        assert call_kwargs["profile_id"] == profile_id
        assert call_kwargs["artifact_type"] == "lesson"

    finally:
        # Clean up overrides
        app.dependency_overrides = {}

def test_get_timeline_profile_not_found():
    """
    Test GET /artifacts/timeline with non-existent profile.
    """
    mock_profile_service = MagicMock(spec=ProfileService)
    mock_profile_service.get_profile.return_value = None

    # We also need to mock memory service because it's in the dependency list
    mock_memory_service = MagicMock(spec=MemoryService)

    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_memory_service] = lambda: mock_memory_service

    client = TestClient(app)

    try:
        params = {
            "profile_id": "non_existent",
            "start_date": "2023-10-01T00:00:00Z",
            "end_date": "2023-10-01T00:00:00Z"
        }

        response = client.get("/artifacts/timeline", params=params)
        assert response.status_code == 404
        assert "Profile with ID non_existent not found" in response.json()["detail"]
    finally:
        app.dependency_overrides = {}

def test_get_timeline_invalid_date_format():
    """
    Test GET /artifacts/timeline with bad date format.
    """
    # Even for invalid date, we might hit dependencies first, so it's safer to mock them
    mock_profile_service = MagicMock(spec=ProfileService)
    mock_profile_service.get_profile.return_value = True

    mock_memory_service = MagicMock(spec=MemoryService)

    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_memory_service] = lambda: mock_memory_service

    client = TestClient(app)

    try:
        params = {
            "profile_id": "p1",
            "start_date": "bad-date",
            "end_date": "2023-10-01T00:00:00Z"
        }

        response = client.get("/artifacts/timeline", params=params)
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]
    finally:
        app.dependency_overrides = {}
