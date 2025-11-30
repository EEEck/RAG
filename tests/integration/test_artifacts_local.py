import uuid
import pytest
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from app.models.artifact import Artifact
from tests.utils.sqlite_test_db import SQLiteTestDB
from app.services.memory_service import MemoryService

@pytest.fixture
def sqlite_db(tmp_path):
    """Fixture to provide a configured SQLiteTestDB."""
    db_path = str(tmp_path / "test_rag.db")
    db = SQLiteTestDB(db_path=db_path)
    db.ensure_schema()
    return db

@pytest.fixture
def mock_embedding_client():
    """Mock OpenAI client for embeddings."""
    mock = MagicMock()
    # Return a dummy vector of length 3 for simplicity
    mock.embeddings.create.return_value.data[0].embedding = [0.1, 0.2, 0.3]
    return mock

@pytest.fixture
def memory_service(sqlite_db, mock_embedding_client):
    """
    Creates a MemoryService instance with patched dependencies.
    """
    with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-key"}):
        with patch("app.services.memory_service.OpenAI") as MockOpenAI:
            MockOpenAI.return_value = mock_embedding_client

            # Instantiate service
            service = MemoryService()

            # Patch the repository to use SQLite
            service.repo = sqlite_db

            return service

def test_save_and_retrieve_artifact(memory_service, sqlite_db):
    """
    Test the artifact saving and retrieval logic using the SQLite mock DB.
    """
    # 1. Setup Profile
    profile_id = "teacher_123"
    sqlite_db.insert_profile(
        id=profile_id,
        user_id="user_abc",
        name="Test Teacher",
        grade_level="1st Grade",
        pedagogy_config={"style": "visual"},
        content_scope={}
    )

    # 2. Create an Artifact
    artifact = Artifact(
        id=uuid.uuid4(),
        profile_id=profile_id,
        type="quiz", # VALID TYPE
        content="Question 1: What is a cat?",
        summary="A simple quiz about animals.",
        created_at=datetime.now(timezone.utc),
        embedding=[0.1, 0.2, 0.3],
        related_book_ids=[],
        topic_tags=["animals", "biology"]
    )

    # 3. Save Artifact (Directly to repo for test setup)
    sqlite_db.save_artifact(artifact)

    # 4. Search Artifacts via Service
    query = "animals"
    hits = memory_service.search_artifacts(profile_id, query=query, limit=1)

    # 5. Verify
    assert len(hits) == 1
    hit = hits[0]
    # MemoryService returns generic AtomHit objects
    # Inspecting memory_service.py: "content_type" is put into metadata
    assert "Question 1" in hit.content
    assert hit.metadata["content_type"] == "quiz" # FIXED: Key is content_type not type

    print("\nSuccessfully retrieved artifact via MemoryService (SQLite backed)!")

def test_artifact_isolation(memory_service, sqlite_db):
    """Ensure artifacts from one profile don't leak to another."""

    # Profile A
    p1 = "teacher_A"
    sqlite_db.save_artifact(Artifact(
        id=uuid.uuid4(), profile_id=p1, type="lesson", content="Secret A",
        created_at=datetime.now(timezone.utc), embedding=[1,0,0]
    ))

    # Profile B
    p2 = "teacher_B"
    sqlite_db.save_artifact(Artifact(
        id=uuid.uuid4(), profile_id=p2, type="lesson", content="Secret B",
        created_at=datetime.now(timezone.utc), embedding=[1,0,0]
    ))

    # Search as Profile A
    hits_a = memory_service.search_artifacts(p1, query="Secret", limit=10)
    assert len(hits_a) == 1
    assert "Secret A" in hits_a[0].content

    # Search as Profile B
    hits_b = memory_service.search_artifacts(p2, query="Secret", limit=10)
    assert len(hits_b) == 1
    assert "Secret B" in hits_b[0].content
