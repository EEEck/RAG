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

@patch("app.services.search.embed_texts")
@patch("app.services.search.get_conn")
@patch("app.services.search.get_settings")
def test_search_route(mock_get_settings, mock_get_conn, mock_embed_texts):
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.embed_model = "test-model"
    mock_get_settings.return_value = mock_settings

    # Mock embeddings
    mock_embed_texts.return_value = [[0.1, 0.2, 0.3]]

    # Mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock DB results
    # First query is for lessons: id, unit, lesson_code, title, score
    mock_cursor.fetchall.side_effect = [
        [(1, 1, "L1", "Lesson 1", 0.9)],
        [(1, 1, "L1", "hello", 0.8)]
    ]

    response = client.post("/search", json={
        "query": "hello",
        "top_lessons": 5,
        "top_vocab": 5
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["lessons"]) == 1
    assert data["lessons"][0]["lesson_code"] == "L1"
    assert len(data["vocab"]) == 1
    assert data["vocab"][0]["term"] == "hello"
