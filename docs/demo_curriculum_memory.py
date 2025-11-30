import os
import json
import uuid
from typing import List
from dotenv import load_dotenv

# Assuming we are running this from root or with pythonpath set
from app.services.memory_service import MemoryService
from app.infra.artifact_db import ArtifactRepository
from app.models.artifact import Artifact

# Load environment variables
load_dotenv()

def demo_curriculum_memory():
    """
    Demonstrates saving generated content as artifacts and searching for them using vector similarity.
    This script mimics the flow of:
    1. A teacher generating a lesson (simulated here).
    2. Saving that lesson to 'Memory' (Postgres + pgvector).
    3. Retrieving it later using a semantic query.
    """
    print("--- Starting Curriculum Memory Demo ---")

    # 1. Initialize Service
    # We use the real service which connects to Postgres and OpenAI
    repo = ArtifactRepository()
    try:
        repo.ensure_schema()
        print("✅ Schema ensured.")
    except Exception as e:
        print(f"⚠️  Database connection failed or schema error: {e}")
        print("Please ensure docker-compose is up and .env is set.")
        return

    memory_service = MemoryService(repo=repo)

    # Generate a dummy profile ID for this demo
    profile_id = f"demo_teacher_{uuid.uuid4().hex[:8]}"
    print(f"👤 Using Profile ID: {profile_id}")

    # 2. Simulate Content to Save
    # Imagine the AI just generated this lesson plan
    lesson_content = """
    Topic: Photosynthesis
    Level: Grade 5 Science

    Introduction:
    Plants make their own food using sunlight. This process is called photosynthesis.
    They need three things: Carbon Dioxide, Water, and Sunlight.

    Activity:
    Draw a plant and label the leaves capturing sunlight.
    """

    lesson_summary = "Grade 5 introduction to Photosynthesis: inputs (sun, water, CO2) and drawing activity."

    print("\n💾 Saving Artifact 1: Photosynthesis Lesson...")
    artifact_1 = memory_service.save_artifact(
        profile_id=profile_id,
        content=lesson_content,
        artifact_type="lesson",
        summary=lesson_summary,
        related_book_ids=["science_textbook_v1"],
        topic_tags=["biology", "plants"]
    )
    print(f"   -> Saved with ID: {artifact_1.id}")

    # Save a second, different artifact
    quiz_content = """
    Quiz: Basic Multiplication
    1. 5 x 5 = ?
    2. 3 x 4 = ?
    3. 10 x 2 = ?
    """
    quiz_summary = "Math quiz on single digit multiplication."

    print("\n💾 Saving Artifact 2: Math Quiz...")
    artifact_2 = memory_service.save_artifact(
        profile_id=profile_id,
        content=quiz_content,
        artifact_type="quiz",
        summary=quiz_summary,
        topic_tags=["math"]
    )
    print(f"   -> Saved with ID: {artifact_2.id}")

    # 3. Demonstrate Semantic Search
    # "What did I teach about plants?" -> Should find the photosynthesis lesson
    query = "activities about plants and sun"
    print(f"\n🔍 Searching Memory for: '{query}'")

    hits = memory_service.search_artifacts(profile_id, query=query, limit=1)

    if hits:
        print(f"✅ Found {len(hits)} result(s):")
        for hit in hits:
            print(f"   - Score: {hit.score}")
            print(f"   - Type: {hit.metadata.get('content_type')}")
            print(f"   - Preview: {hit.content[:100]}...")
    else:
        print("❌ No results found (Check if OpenAI embeddings are working).")

    # 4. Cleanup (Optional, for demo hygiene)
    # In a real app we wouldn't delete, but here we might want to keep the DB clean-ish
    # skipping cleanup to allow manual inspection if needed.

    print("\n--- Demo Complete ---")

if __name__ == "__main__":
    demo_curriculum_memory()
