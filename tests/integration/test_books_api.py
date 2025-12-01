import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.constants import SubjectCategory, STANDARD_SUBJECTS
from ingest.infra.postgres import PostgresStructureNodeRepository
from typing import List, Dict, Any, Optional
import difflib

# Mock Repository
class MockStructureNodeRepository:
    def __init__(self, books_data: List[Dict[str, Any]]):
        self.books_data = books_data

    def ensure_schema(self):
        pass

    def insert_structure_nodes(self, nodes):
        pass

    def list_books(self, subject: str, title: Optional[str] = None, level: Optional[int] = None, min_level: Optional[int] = None, max_level: Optional[int] = None, excluded_subjects: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        results = []
        for b in self.books_data:
            meta = b.get("metadata", {})
            b_subject = meta.get("subject", "unknown")
            b_title = b.get("title", "")
            b_level = int(meta.get("grade_level", 0))

            # Subject Logic
            if subject == 'other' and excluded_subjects:
                if b_subject in excluded_subjects:
                    continue
            elif subject != 'other':
                if b_subject != subject:
                    continue

            # Title Logic (Partial Match + Fuzzy Sim)
            if title:
                # 1. Partial Match (ILIKE)
                match = title.lower() in b_title.lower()

                # 2. Fuzzy Match (simulating pg_trgm % operator)
                # This assumes comparing the whole query against the whole title (or close to it)
                if not match:
                    matcher = difflib.SequenceMatcher(None, title.lower(), b_title.lower())
                    # "Histry" vs "History" is 0.92
                    if matcher.ratio() > 0.6:
                        match = True

                if not match:
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
        {"book_id": "3", "title": "History", "metadata": {"subject": "history", "grade_level": 3}}, # Renamed for simpler fuzzy test
        {"book_id": "4", "title": "English 2", "metadata": {"subject": "language", "grade_level": 2}},
        {"book_id": "5", "title": "Art 101", "metadata": {"subject": "arts", "grade_level": 1}}, # Other subject
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

def test_list_books_other_subject(client):
    # Search for 'other' should find 'arts'
    response = client.get("/books/?subject=other&level=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Art 101"

def test_list_books_title_search(client):
    # Search for 'Math'
    response = client.get("/books/?subject=stem&level=1&title=Math")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Math 1"

def test_list_books_title_partial(client):
    # Search for 'hist' (partial)
    response = client.get("/books/?subject=history&level=3&title=hist")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "History"

def test_list_books_title_typo_fuzzy(client):
    # Search for 'Histry' (typo of History)
    response = client.get("/books/?subject=history&level=3&title=Histry")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "History"

def test_list_books_title_no_match(client):
    response = client.get("/books/?subject=stem&level=1&title=Physics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
