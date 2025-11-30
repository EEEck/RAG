import pytest
from fastapi.testclient import TestClient
from app.main import app
from ingest.infra.postgres import PostgresStructureNodeRepository
from typing import List, Dict, Any, Optional

# Mock Repository
class MockStructureNodeRepository:
    def __init__(self, books_data: List[Dict[str, Any]]):
        self.books_data = books_data

    def ensure_schema(self):
        pass

    def insert_structure_nodes(self, nodes):
        pass

    def list_books(self, subject: str, level: Optional[int] = None, min_level: Optional[int] = None, max_level: Optional[int] = None) -> List[Dict[str, Any]]:
        results = []
        for b in self.books_data:
            meta = b.get("metadata", {})
            b_subject = meta.get("subject", "unknown")
            b_level = int(meta.get("grade_level", 0))

            if b_subject != subject:
                continue

            # Match production logic: if level is present, ignore range
            if level is not None:
                if b_level != level:
                    continue
            elif min_level is not None and max_level is not None:
                if not (min_level <= b_level <= max_level):
                    continue

            results.append(b)
        return results

# Fixture to override dependency
@pytest.fixture
def client():
    # Setup mock data
    mock_books = [
        {"book_id": "1", "title": "Math 1", "metadata": {"subject": "stem", "grade_level": 1}},
        {"book_id": "2", "title": "Math 5", "metadata": {"subject": "stem", "grade_level": 5}},
        {"book_id": "3", "title": "History 3", "metadata": {"subject": "history", "grade_level": 3}},
        {"book_id": "4", "title": "English 2", "metadata": {"subject": "language", "grade_level": 2}},
    ]

    repo = MockStructureNodeRepository(mock_books)

    # Override dependency
    from app.routes.books import get_structure_repo
    app.dependency_overrides[get_structure_repo] = lambda: repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

def test_list_books_missing_params(client):
    response = client.get("/books/")
    assert response.status_code == 422 # Missing required subject

def test_list_books_missing_level_filter(client):
    response = client.get("/books/?subject=stem")
    assert response.status_code == 400
    assert "Mandatory filtering required" in response.json()["detail"]

def test_list_books_exact_level(client):
    response = client.get("/books/?subject=stem&level=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Math 1"

def test_list_books_range_level(client):
    response = client.get("/books/?subject=stem&min_level=1&max_level=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {b["title"] for b in data}
    assert "Math 1" in titles
    assert "Math 5" in titles

def test_list_books_subject_mismatch(client):
    response = client.get("/books/?subject=history&level=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_list_books_mixed_filters(client):
    # Both level and range provided, behavior depends on implementation priority or intersection
    # Our impl: level takes precedence in mock?
    # Actually implementation in postgres.py handles `if level: ... elif range: ...`
    # So level takes precedence.
    response = client.get("/books/?subject=stem&level=1&min_level=3&max_level=6")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Math 1"
