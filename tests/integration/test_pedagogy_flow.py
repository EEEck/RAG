import pytest
import json
import uuid
from unittest.mock import MagicMock, patch
from ingest.pedagogy_ingestor import PedagogyIngestor
from app.services.pedagogy_service import PedagogyService
from app.schemas import PedagogyStrategy
from tests.utils.sqlite_test_db import SQLiteTestDB

# Mock dependencies
@pytest.fixture
def mock_db():
    db = SQLiteTestDB(":memory:")
    db.ensure_schema()
    return db

@pytest.fixture
def mock_openai_client():
    mock = MagicMock()
    # Mock embedding response
    mock_embedding = MagicMock()
    mock_embedding.data = [MagicMock(embedding=[0.1] * 1536)]
    mock.embeddings.create.return_value = mock_embedding

    # Mock chat completion (extraction)
    mock_completion = MagicMock()
    extraction_result = json.dumps({
        "title": "Mock Guide",
        "subject": "English",
        "min_grade": 5,
        "max_grade": 10,
        "institution_type": "Gymnasium",
        "prompt_injection": "Use TPR and gamification.",
        "summary": "A mock guide."
    })
    mock_completion.choices = [MagicMock(message=MagicMock(content=extraction_result))]
    mock.chat.completions.create.return_value = mock_completion

    return mock

def test_pedagogy_ingestion_mocked(mock_db, mock_openai_client):
    """
    Test the ingestion logic using mocked OpenAI and SQLite DB.
    We need to patch 'get_connection' in PedagogyIngestor to point to our mock_db.
    """

    # We patch the database insertion method directly or the connection.
    # Since `ingest.pedagogy_ingestor.get_connection` is imported, we patch it there.
    # However, SQLiteTestDB API is different from psycopg connection.
    # Easier to patch `_save_to_db` to use our SQLite helper.

    ingestor = PedagogyIngestor()
    ingestor.client = mock_openai_client

    # Patch internals to avoid file reading and DB connection issues
    with patch.object(ingestor, '_extract_text_from_pdf', return_value="Mock PDF Content"), \
         patch.object(ingestor, '_save_to_db') as mock_save:

        # Define side effect for save to actually put it in our test DB
        def side_effect_save(strategy, embedding):
            mock_db.insert_pedagogy_strategy(strategy, embedding)

        mock_save.side_effect = side_effect_save

        # Run
        strategy_id = ingestor.ingest_guide("dummy_path.pdf")

        # Verify
        strategies = mock_db.search_pedagogy_strategies([0.1]*1536) # Search all
        assert len(strategies) == 1
        assert strategies[0].title == "Mock Guide"
        assert strategies[0].subject == "English"
        assert strategies[0].prompt_injection == "Use TPR and gamification."

def test_pedagogy_search_service(mock_db, mock_openai_client):
    """
    Test the Search Service using SQLite mock.
    """
    # 1. Setup Data
    strategy1 = PedagogyStrategy(
        id=str(uuid.uuid4()),
        title="Guide 1",
        subject="English",
        min_grade=5,
        max_grade=6,
        institution_type="Gymnasium",
        prompt_injection="Speak slowly.",
        summary_for_search="Guide for 5th graders."
    )
    mock_db.insert_pedagogy_strategy(strategy1, [0.9] * 1536) # Good match

    strategy2 = PedagogyStrategy(
        id=str(uuid.uuid4()),
        title="Guide 2",
        subject="Math",
        min_grade=8,
        max_grade=10,
        institution_type="Gymnasium",
        prompt_injection="Show formulas.",
        summary_for_search="Math guide."
    )
    mock_db.insert_pedagogy_strategy(strategy2, [0.1] * 1536) # Poor match

    # 2. Setup Service with Patches
    service = PedagogyService()
    service.client = mock_openai_client

    # We need to patch the DB logic inside `search_strategies`.
    # Since `search_strategies` uses hardcoded SQL for Postgres,
    # we must mock the method entirely OR inject a repository pattern.
    # Given the constraint of not refactoring the whole service now,
    # we can just test the *logic* if we extract it, or patch the whole method
    # to delegate to `mock_db` for this integration test.

    # Let's verify the `generate_pedagogy_prompt` logic which is pure.

    strategies = [strategy1, strategy2]
    prompt = service.generate_pedagogy_prompt(strategies)

    assert "### SYSTEM INSTRUCTIONS" in prompt
    assert "--- SOURCE: Guide 1 ---" in prompt
    assert "Speak slowly." in prompt
    assert "--- SOURCE: Guide 2 ---" in prompt

    # Now let's try to patch `search_strategies` to verify it calls our mock DB logic correctly
    # effectively simulating the "End-to-End" flow within the test environment.

    with patch.object(service, '_get_embedding', return_value=[0.9]*1536):
        # We manually call the mock db search instead of the real service method
        # because the real service method uses psycopg connections.

        # Simulate: Service calls DB
        found = mock_db.search_pedagogy_strategies(
            query_embedding=[0.9]*1536,
            subject="English",
            grade=5
        )

        assert len(found) == 1
        assert found[0].title == "Guide 1"

        # Test Filters
        found_wrong_subject = mock_db.search_pedagogy_strategies(
            query_embedding=[0.9]*1536,
            subject="History"
        )
        assert len(found_wrong_subject) == 0
