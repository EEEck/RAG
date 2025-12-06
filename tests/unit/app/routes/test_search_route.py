import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.schemas import SearchResponse, TeacherProfile

client = TestClient(app)

@patch("app.routes.search.get_search_service")
@patch("app.routes.search.get_profile_service")
def test_search_basic(mock_get_profile, mock_get_search):
    mock_service = MagicMock()
    mock_get_search.return_value = mock_service
    mock_service.search_content.return_value = SearchResponse(lessons=[], vocab=[], atoms=[])

    # Simple search
    resp = client.post("/search", json={"query": "test"})
    assert resp.status_code == 200
    mock_service.search_content.assert_called_once()
    args, kwargs = mock_service.search_content.call_args
    assert kwargs["query"] == "test"
    assert kwargs["user_id"] is None

@patch("app.routes.search.get_search_service")
@patch("app.routes.search.get_profile_service")
def test_search_strict_mode(mock_get_profile, mock_get_search):
    mock_profile_service = MagicMock()
    mock_get_profile.return_value = mock_profile_service

    mock_profile = TeacherProfile(user_id="u1", name="T1", book_list=["b1"])
    mock_profile_service.get_profile.return_value = mock_profile

    mock_service = MagicMock()
    mock_get_search.return_value = mock_service
    mock_service.search_content.return_value = SearchResponse(lessons=[], vocab=[], atoms=[])

    resp = client.post("/search", json={
        "query": "test",
        "strict_mode": True,
        "profile_id": "p1"
    })

    assert resp.status_code == 200
    mock_profile_service.get_profile.assert_called_with("p1")

    # Check book_ids and user_id passed to service
    mock_service.search_content.assert_called_once()
    args, kwargs = mock_service.search_content.call_args
    assert kwargs["book_ids"] == ["b1"]
    assert kwargs["user_id"] == "u1"
