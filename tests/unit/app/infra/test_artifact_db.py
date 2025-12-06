import pytest
from unittest.mock import MagicMock, patch
from app.infra.artifact_db import ArtifactRepository
from app.models.artifact import Artifact
import uuid
from datetime import datetime

@patch("app.infra.artifact_db.get_conn")
def test_save_artifact(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    repo = ArtifactRepository()
    art = Artifact(id=uuid.uuid4(), profile_id="p1", content="c", created_at=datetime.utcnow(), type="lesson", embedding=[0.1])

    repo.save_artifact(art)
    mock_cur.execute.assert_called()

@patch("app.infra.artifact_db.get_conn")
def test_search_artifacts(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # Mock data return (tuples expected)
    mock_cur.fetchall.return_value = [
        (uuid.uuid4(), "p1", "lesson", "c", "summary", datetime.utcnow(), None, [], [])
    ]

    repo = ArtifactRepository()
    results = repo.search_artifacts("p1", limit=1)
    assert len(results) == 1
    mock_cur.execute.assert_called()
