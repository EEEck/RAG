from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("app.main.get_settings")
@patch("app.main.os.getenv")
def test_config_preview(mock_getenv, mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.pg_dsn = "postgres://user:pass@localhost:5432/db"
    mock_settings.embed_model = "test-model"
    mock_get_settings.return_value = mock_settings
    mock_getenv.return_value = "fake-key"

    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert data["openai_key_present"] == "true"
    assert data["postgres_dsn"] == "postgres://user:pass@localhost:5432/db"
    assert data["embed_model"] == "test-model"

@patch("app.routes.search.get_search_service")
def test_search_route(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    # Setup mock response from service
    from app.schemas import SearchResponse, AtomHit, LessonHit, VocabHit
    mock_service.search_content.return_value = SearchResponse(
        lessons=[],
        vocab=[],
        atoms=[
             AtomHit(id="1", content="Lesson 1 Content", metadata={"lesson_code": "L1", "title": "Lesson 1", "atom_type": "lesson"}, score=0.9),
             AtomHit(id="2", content="hello definition", metadata={"term": "hello", "atom_type": "vocab"}, score=0.8)
        ]
    )

    response = client.post("/search", json={
        "query": "hello",
        "book_id": "test_book"
    })

    assert response.status_code == 200
    data = response.json()
    # The new API returns a flat list of atoms in 'atoms', not 'lessons'/'vocab'
    assert "atoms" in data
    assert len(data["atoms"]) == 2
    assert data["atoms"][0]["metadata"]["lesson_code"] == "L1"
