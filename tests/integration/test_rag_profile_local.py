import uuid
import pytest
from unittest.mock import MagicMock, patch
from ingest.models import StructureNode, ContentAtom
from app.schemas import AtomHit # Correct import
from tests.utils.sqlite_test_db import SQLiteTestDB
from app.rag_engine import retrieve_and_generate
from app.services.search_service import SearchService

# Mock Data for RAG
MOCK_PROFILE_ID = "profile_esl_1"
MOCK_PEDAGOGY = {
    "tone": "encouraging", # Correct field from schema
    "style": "visual",
    "focus_areas": ["vocabulary"],
    "adaptation_level": "beginner"
}

@pytest.fixture
def sqlite_db(tmp_path):
    db_path = str(tmp_path / "test_rag_profile.db")
    db = SQLiteTestDB(db_path=db_path)
    db.ensure_schema()

    # Insert Mock Profile
    db.insert_profile(
        id=MOCK_PROFILE_ID,
        user_id="user_1",
        name="Mr. Test",
        grade_level="1",
        pedagogy_config=MOCK_PEDAGOGY,
        content_scope={}
    )
    return db

@pytest.fixture
def mock_search_service():
    """Mocks SearchService to return static results."""
    mock = MagicMock(spec=SearchService)

    # Mock return value for search_content
    # SearchResponse contains .atoms
    from app.schemas import SearchResponse

    hit = AtomHit(
        id=str(uuid.uuid4()),
        content="The cat sat on the mat. It is a fat cat.",
        score=0.9,
        metadata={"category": "language", "unit": 1}
    )

    response = SearchResponse(
        lessons=[],
        vocab=[],
        atoms=[hit]
    )

    mock.search_content.return_value = response
    return mock

@pytest.fixture
def mock_llm_generation():
    """Patches the LLM generation to avoid API calls."""
    with patch("app.rag_engine.generate_items") as mock:
        from app.schemas import GenerateItemsResponse, ScopeReport
        mock.return_value = GenerateItemsResponse(
            items=[],
            scope_report=ScopeReport(violations=0)
        )
        yield mock

def test_rag_with_profile_context(sqlite_db, mock_search_service, mock_llm_generation):
    """
    Test that the RAG pipeline retrieves the profile's pedagogy config
    and passes it to the generation step.
    """

    # Define a side effect to fetch profile from our SQLite DB
    def get_profile_side_effect(pid):
        p_data = sqlite_db.get_profile(pid)
        if not p_data:
            return None
        from app.schemas import TeacherProfile
        return TeacherProfile(**p_data)

    # Patch get_profile_service() to return a mock service
    # app/rag_engine.py imports: from .services.profile_service import get_profile_service
    # So we patch "app.rag_engine.get_profile_service"

    with patch("app.rag_engine.get_profile_service") as mock_get_service_fn:
        # Create a mock service instance
        mock_service = MagicMock()
        mock_service.get_profile.side_effect = get_profile_side_effect
        mock_get_service_fn.return_value = mock_service

        # Patch get_search_service() as well
        with patch("app.rag_engine.get_search_service") as mock_get_search:
            mock_get_search.return_value = mock_search_service

            # Execute RAG
            # Signature: retrieve_and_generate(book_id, unit, topic, category, profile_id, use_memory)
            retrieve_and_generate(
                book_id="book-123",
                unit=1,
                topic="cats",
                profile_id=MOCK_PROFILE_ID,
                use_memory=False
            )

            # Verify Profile Fetch
            mock_service.get_profile.assert_called_with(MOCK_PROFILE_ID)

            # Verify LLM Generation call
            call_args = mock_llm_generation.call_args
            assert call_args is not None, "generate_items was not called"

            # Check kwargs for pedagogy_config
            pedagogy_config = call_args.kwargs.get('pedagogy_config')
            assert pedagogy_config is not None, "PedagogyConfig was not passed to generation"

            # Check values
            assert pedagogy_config.tone == "encouraging"
            assert "vocabulary" in pedagogy_config.focus_areas

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-s", __file__]))
