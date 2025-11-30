import os
import sys
import uuid
import json

# Add the project root to the path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.profile_service import get_profile_service
from app.schemas import TeacherProfile, PedagogyConfig
from app.rag_engine import retrieve_and_generate
from ingest.infra.postgres import PostgresStructureNodeRepository

def main():
    print("--- Starting Classroom Profiles Demo ---\n")

    # 1. Ensure DB Schema (for demo purposes)
    print("1. Ensuring Database Schema exists...")
    try:
        repo = PostgresStructureNodeRepository()
        repo.ensure_schema()
        print("   Schema verified.\n")
    except Exception as e:
        print(f"   Error connecting to DB: {e}")
        print("   Make sure you are running this where POSTGRES_HOST is accessible.")
        return

    # 2. Create Profiles
    service = get_profile_service()

    # Profile A: Pirate
    pirate_profile = TeacherProfile(
        user_id="demo_user",
        name="Captain Blackbeard",
        grade_level="5",
        pedagogy_config=PedagogyConfig(
            tone="pirate",
            style="adventurous",
            focus_areas=["nautical terms", "excitement"]
        )
    )

    # Profile B: Academic
    academic_profile = TeacherProfile(
        user_id="demo_user",
        name="Professor Higgins",
        grade_level="12",
        pedagogy_config=PedagogyConfig(
            tone="formal",
            style="strict",
            adaptation_level="advanced"
        )
    )

    print(f"2. Creating Profile A: {pirate_profile.name} (Tone: {pirate_profile.pedagogy_config.tone})")
    created_pirate = service.create_profile(pirate_profile)
    print(f"   Created ID: {created_pirate.id}\n")

    print(f"3. Creating Profile B: {academic_profile.name} (Tone: {academic_profile.pedagogy_config.tone})")
    created_academic = service.create_profile(academic_profile)
    print(f"   Created ID: {created_academic.id}\n")

    # 3. Simulate RAG Requests
    print("4. Simulating RAG Generation Requests...")

    # We need a valid book_id, usually from ingest.
    # For this demo, we use a random UUID, which will result in "No content found" context,
    # but the *Profile* instructions will still be injected into the system prompt.
    dummy_book_id = str(uuid.uuid4())
    topic = "The Water Cycle"

    print(f"   Generating for {created_pirate.name}...")
    try:
        # Note: This requires OPENAI_API_KEY to be set and working
        response_pirate = retrieve_and_generate(
            book_id=dummy_book_id,
            unit=1,
            topic=topic,
            profile_id=created_pirate.id
        )
        print("   [Pirate Response Items]:")
        for item in response_pirate.items[:1]: # Print first item
            print(f"   - Stem: {item.stem}")
            print(f"   - Answer: {item.answer}\n")

    except Exception as e:
        print(f"   Generation failed (expected if no OpenAI Key): {e}\n")

    print(f"   Generating for {created_academic.name}...")
    try:
        response_academic = retrieve_and_generate(
            book_id=dummy_book_id,
            unit=1,
            topic=topic,
            profile_id=created_academic.id
        )
        print("   [Academic Response Items]:")
        for item in response_academic.items[:1]:
            print(f"   - Stem: {item.stem}")
            print(f"   - Answer: {item.answer}\n")

    except Exception as e:
        print(f"   Generation failed: {e}\n")

    print("--- Demo Complete ---")

if __name__ == "__main__":
    main()
