import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.routes.artifacts import get_memory_service, get_profile_service
from app.schemas import TeacherProfile, AtomHit, TimelineArtifact

client = TestClient(app)

@pytest.fixture
def mocks():
    mock_memory = MagicMock()
    mock_profile = MagicMock()
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    app.dependency_overrides[get_profile_service] = lambda: mock_profile
    yield mock_memory, mock_profile
    app.dependency_overrides = {}

def test_save_artifact_success(mocks):
    mock_memory, mock_profile = mocks
    mock_profile.get_profile.return_value = TeacherProfile(user_id="u1", name="T1")

    mock_artifact = MagicMock()
    mock_artifact.id = "art1"
    mock_artifact.profile_id = "p1"
    mock_artifact.type = "lesson"
    mock_artifact.created_at = datetime(2023, 1, 1)

    mock_memory.save_artifact.return_value = mock_artifact

    resp = client.post("/artifacts/", json={
        "profile_id": "p1",
        "content": "some content",
        "type": "lesson"
    })

    assert resp.status_code == 200
    assert resp.json()["id"] == "art1"

    mock_memory.save_artifact.assert_called_once()

def test_save_artifact_profile_not_found(mocks):
    mock_memory, mock_profile = mocks
    mock_profile.get_profile.return_value = None

    resp = client.post("/artifacts/", json={
        "profile_id": "p99",
        "content": "content"
    })

    assert resp.status_code == 404

def test_list_artifacts(mocks):
    mock_memory, mock_profile = mocks
    mock_profile.get_profile.return_value = TeacherProfile(user_id="u1", name="T1")

    mock_memory.search_artifacts.return_value = [
        AtomHit(id="1", content="c1", metadata={}, score=0.9)
    ]

    resp = client.get("/artifacts/?profile_id=p1&query=test")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

def test_timeline_success(mocks):
    mock_memory, mock_profile = mocks
    mock_profile.get_profile.return_value = TeacherProfile(user_id="u1", name="T1")

    mock_art = MagicMock()
    mock_art.id = "1"
    mock_art.created_at = datetime(2023, 1, 15)
    mock_art.type = "quiz"
    mock_art.summary = "A quiz"

    mock_memory.get_artifacts_in_range.return_value = [mock_art]

    resp = client.get("/artifacts/timeline?profile_id=p1&start_date=2023-01-01&end_date=2023-02-01")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "A quiz"

def test_timeline_invalid_date(mocks):
    mock_memory, mock_profile = mocks
    mock_profile.get_profile.return_value = TeacherProfile(user_id="u1", name="T1")

    resp = client.get("/artifacts/timeline?profile_id=p1&start_date=invalid&end_date=2023-02-01")
    assert resp.status_code == 400
