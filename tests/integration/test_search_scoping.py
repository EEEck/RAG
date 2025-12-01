import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import SearchResponse, TeacherProfile

client = TestClient(app)

# We must patch where the function is USED, which is app.routes.search
@patch("app.routes.search.get_profile_service")
@patch("app.routes.search.get_search_service")
def test_search_strict_mode_no_books(mock_get_search, mock_get_profile):
    """Verify that strict mode raises 400 when profile has no books."""

    # Setup Mocks
    mock_profile_service = MagicMock()
    mock_get_profile.return_value = mock_profile_service

    # Mock Profile with empty book list
    mock_profile = TeacherProfile(
        id="profile_123",
        user_id="user_123",
        name="Test Teacher",
        book_list=[]
    )
    mock_profile_service.get_profile.return_value = mock_profile

    payload = {
        "query": "photosynthesis",
        "profile_id": "profile_123",
        "strict_mode": True
    }

    response = client.post("/search", json=payload)

    assert response.status_code == 400
    assert "no books are assigned" in response.json()["detail"]

@patch("app.routes.search.get_profile_service")
@patch("app.routes.search.get_search_service")
def test_search_strict_mode_with_books(mock_get_search, mock_get_profile):
    """Verify that strict mode proceeds when profile has books."""

    # Setup Mocks
    mock_profile_service = MagicMock()
    mock_get_profile.return_value = mock_profile_service

    mock_search_service = MagicMock()
    mock_get_search.return_value = mock_search_service

    # Mock Profile with books
    mock_profile = TeacherProfile(
        id="profile_123",
        user_id="user_123",
        name="Test Teacher",
        book_list=["book_abc"]
    )
    mock_profile_service.get_profile.return_value = mock_profile

    # Mock Search Service Response
    mock_search_service.search_content.return_value = SearchResponse(
        lessons=[], vocab=[], atoms=[]
    )

    payload = {
        "query": "photosynthesis",
        "profile_id": "profile_123",
        "strict_mode": True
    }

    response = client.post("/search", json=payload)

    assert response.status_code == 200

    # Ensure book_ids passed to service matches profile's list
    mock_search_service.search_content.assert_called_once()
    call_args = mock_search_service.search_content.call_args
    assert call_args.kwargs['book_ids'] == ["book_abc"]

def test_search_strict_mode_missing_profile():
    """Verify that strict mode raises 400 if profile_id is missing."""

    payload = {
        "query": "photosynthesis",
        "strict_mode": True
    }

    response = client.post("/search", json=payload)

    assert response.status_code == 400
    assert "Profile ID is required" in response.json()["detail"]
