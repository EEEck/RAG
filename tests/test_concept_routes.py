from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@patch("app.services.concept_pack.embed_texts")
@patch("app.services.concept_pack.get_conn")
@patch("app.services.concept_pack.get_settings")
def test_concept_pack_route(mock_get_settings, mock_get_conn, mock_embed_texts):
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
    # 1. Anchor lesson
    mock_cursor.fetchone.return_value = (1, 5, "L5", "Lesson 5", "Lesson 5 body")

    # 2. Scope lessons (fetch all)
    mock_cursor.fetchall.side_effect = [
        [(1, 1, "L1", "Lesson 1"), (2, 2, "L2", "Lesson 2"), (3, 5, "L5", "Lesson 5")], # Scope lessons
        [(2, 2, "L2", "Lesson 2")], # Neighbor lessons
        [("apple",), ("banana",)] # Vocab terms
    ]

    response = client.post("/concept/pack", json={
        "textbook_id": "TB1",
        "lesson_code": "L5"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["anchor_lesson_id"] == 1
    assert data["allowed_scope_count"] == 3
    assert "apple" in data["concept_pack"]["vocab"]
    assert "banana" in data["concept_pack"]["vocab"]

@patch("app.services.concept_pack.get_conn")
@patch("app.services.concept_pack.get_settings")
def test_concept_pack_not_found(mock_get_settings, mock_get_conn):
    mock_settings = MagicMock()
    mock_get_settings.return_value = mock_settings

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Anchor lesson return None
    mock_cursor.fetchone.return_value = None

    # TestClient raises exceptions by default to help debugging
    import pytest
    with pytest.raises(ValueError, match="Anchor lesson not found"):
        client.post("/concept/pack", json={
            "textbook_id": "TB1",
            "lesson_code": "MISSING"
        })

@patch("app.services.generation.get_sync_client")
@patch("app.services.generation.get_settings")
def test_generate_items_route(mock_get_settings, mock_get_client):
    mock_settings = MagicMock()
    mock_settings.chat_model = "gpt-4"
    mock_get_settings.return_value = mock_settings

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock LLM response
    mock_completion = MagicMock()
    mock_message = MagicMock()
    mock_message.text = '{"items": [{"stem": "Q1", "answer": "A1"}]}'
    mock_completion.output = [MagicMock(content=[mock_message])]
    mock_client.responses.create.return_value = mock_completion

    response = client.post("/concept/generate-items", json={
        "textbook_id": "TB1",
        "lesson_code": "L1",
        "concept_pack": {
            "vocab": ["apple"],
            "grammar_rules": [],
            "themes": []
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["stem"] == "Q1"

@patch("app.services.generation.get_sync_client")
@patch("app.services.generation.get_settings")
def test_generate_items_bad_json(mock_get_settings, mock_get_client):
    mock_settings = MagicMock()
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock LLM response with bad JSON
    mock_completion = MagicMock()
    mock_message = MagicMock()
    mock_message.text = 'Not valid JSON'
    mock_completion.output = [MagicMock(content=[mock_message])]
    mock_client.responses.create.return_value = mock_completion

    response = client.post("/concept/generate-items", json={
        "textbook_id": "TB1",
        "lesson_code": "L1",
        "concept_pack": {
            "vocab": ["apple"],
            "grammar_rules": [],
            "themes": []
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0
    assert data["scope_report"]["notes"] == ["Failed to parse JSON"]
