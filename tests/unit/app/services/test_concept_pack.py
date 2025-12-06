import pytest
from unittest.mock import MagicMock, patch
from app.services.concept_pack import build_concept_pack
from app.schemas import ConceptPackRequest

@patch("app.services.concept_pack.get_conn")
@patch("app.services.concept_pack.embed_texts")
def test_build_concept_pack(mock_embed, mock_get_conn):
    # Mock Embed
    mock_embed.return_value = [[0.1, 0.2]]

    # Mock DB
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # Mock Anchor Lesson fetch
    mock_cur.fetchone.return_value = (1, 1, "1.1", "Title", "Body")

    # Mock Scope Lessons
    # First fetchall is for scope_lessons
    # Second fetchall is for neighbor_lessons
    # Third fetchall is for vocab_terms
    mock_cur.fetchall.side_effect = [
        [(1, 1, "1.1", "Title")], # Scope lessons
        [(1, 1, "1.1", "Title")], # Neighbors
        [("apple",), ("banana",)] # Vocab
    ]

    req = ConceptPackRequest(textbook_id="b1", lesson_code="1.1")
    resp = build_concept_pack(req)

    assert resp.anchor_lesson_id == 1
    assert "apple" in resp.concept_pack.vocab
