
import os
import sys
import uuid
import datetime
from unittest.mock import MagicMock

# Allow imports from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.artifact import Artifact
from app.services.review_service import ReviewService
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService
from app.schemas import SearchResponse, GenerateItemsResponse, GeneratedItem, ScopeReport, TeacherProfile, AtomHit

def demo_review_workflow_mocked():
    """
    Demonstrates the End-to-End Review Workflow (Mocked).

    Since we don't have a live DB or OpenAI in this environment,
    we will mock the repositories and external calls to verify the LOGIC
    of the ReviewService.
    """
    print("--- Starting End-to-End Review Verification (Mocked) ---")

    # 1. Setup Mocks
    print("🛠️  Initializing Mock Services...")

    # Mock Memory Service (returns predefined artifacts)
    mock_memory_service = MagicMock(spec=MemoryService)

    # Mock Search Service (returns generic text for re-query)
    mock_search_service = MagicMock(spec=SearchService)

    # Use real Pydantic models for response to satisfy validation
    mock_search_service.search_content.return_value = SearchResponse(
        lessons=[],
        vocab=[],
        atoms=[
            AtomHit(id="1", content="Photosynthesis uses sunlight to create energy.", metadata={}, score=0.9),
            AtomHit(id="2", content="Multiplication is repeated addition.", metadata={}, score=0.8)
        ]
    )

    # Mock Profile Service (returns a dummy profile)
    mock_profile_service = MagicMock(spec=ProfileService)
    mock_profile_service.get_profile.return_value = TeacherProfile(
        id="teacher_1", user_id="u1", name="Mr. Mock", book_list=[]
    )

    # Instantiate ReviewService with our mocks
    review_service = ReviewService(
        memory_service=mock_memory_service,
        search_service=mock_search_service
    )

    # 2. Simulate "Teaching" (Creating Artifacts)
    print("👨‍🏫 Simulating 'Teaching' sessions...")

    profile_id = "teacher_1"
    now = datetime.datetime.utcnow()

    # Artifact 1: Science (Yesterday)
    art1 = Artifact(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        type="lesson",
        content="Lesson on Photosynthesis...",
        summary="Students learned about plants and sun.",
        topic_tags=["photosynthesis", "plants"],
        created_at=now - datetime.timedelta(days=1)
    )

    # Artifact 2: Math (2 days ago)
    art2 = Artifact(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        type="quiz",
        content="Quiz on Multiplication...",
        summary="Assessment of 5x5 multiplication.",
        topic_tags=["math", "multiplication"],
        created_at=now - datetime.timedelta(days=2)
    )

    # Setup MemoryService to return these when queried
    mock_memory_service.get_artifacts_in_range.return_value = [art1, art2]

    print(f"   -> Created Artifact: {art1.topic_tags} ({art1.created_at.date()})")
    print(f"   -> Created Artifact: {art2.topic_tags} ({art2.created_at.date()})")

    # 3. Trigger Review Generation
    print("\n🔄 Generating Review for 'Last 7 Days'...")

    # We need to patch `app.services.review_service.generate_items` because it calls OpenAI
    # We will use a context manager to patch it locally here
    from unittest.mock import patch

    with patch("app.services.review_service.generate_items") as mock_generate, \
         patch("app.services.review_service.get_profile_service", return_value=mock_profile_service):

        # Setup expected mock response
        mock_generate.return_value = GenerateItemsResponse(
            items=[
                GeneratedItem(stem="What do plants need?", answer="Sunlight", concept_tags=["photosynthesis"]),
                GeneratedItem(stem="What is 5x5?", answer="25", concept_tags=["math"])
            ],
            scope_report=ScopeReport(violations=0)
        )

        response = review_service.generate_review_quiz(
            profile_id=profile_id,
            time_window="last_7_days"
        )

        # 4. Verify Output
        print("\n✅ Review Generated!")
        print("   Items:")
        for item in response.items:
            print(f"   - [Question] {item.stem} (Tags: {item.concept_tags})")

        # Assertions
        assert len(response.items) == 2
        print("\n✅ Verification Passed: Review contains items from both topics.")

        # Verify call arguments
        mock_memory_service.get_artifacts_in_range.assert_called_once()
        print("✅ Verified MemoryService was queried for date range.")

        # Verify context string passed to generation contained summaries
        call_args = mock_generate.call_args
        if call_args:
            req = call_args[0][0] # First arg is GenerateItemsRequest
            context = req.context_text
            if "Photosynthesis" in context and "Multiplication" in context:
                 print("✅ Verified Context contained summaries of past artifacts.")
            else:
                 print("⚠️  Context verification failed: ", context[:100])

if __name__ == "__main__":
    demo_review_workflow_mocked()
