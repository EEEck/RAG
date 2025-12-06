import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.routes.books import get_structure_repo

client = TestClient(app)

def test_list_books_missing_params():
    resp = client.get("/books/")
    assert resp.status_code == 422 # Validation error for missing 'subject'

    resp = client.get("/books/?subject=language")
    assert resp.status_code == 400 # Custom check: mandatory level filtering

def test_list_books_success():
    mock_repo = MagicMock()
    # Helper to override dependency
    app.dependency_overrides[get_structure_repo] = lambda: mock_repo

    mock_repo.list_books.return_value = [{
        "book_id": "b1",
        "title": "Book 1",
        "metadata": {"subject": "language", "grade_level": 5}
    }]

    try:
        resp = client.get("/books/?subject=language&level=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Book 1"

        mock_repo.list_books.assert_called_once()
        kwargs = mock_repo.list_books.call_args.kwargs
        assert kwargs["subject"] == "language"
        assert kwargs["level"] == 5
    finally:
        app.dependency_overrides = {}
