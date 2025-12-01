import os
import sys
import uuid
import time
import json
from typing import Optional

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

# --- Environment Configuration ---
# We force the configuration to match the expected split architecture for the notebook.
# This ensures SearchService (which defaults to POSTGRES_HOST) and ArtifactRepository (User DB) work correctly.

# Content DB (Defaults from docker-compose or localhost)
CONTENT_DB_HOST = os.getenv("POSTGRES_CONTENT_HOST", "localhost")
CONTENT_DB_PORT = os.getenv("POSTGRES_CONTENT_PORT", "5433")

# User DB
USER_DB_HOST = os.getenv("POSTGRES_USER_HOST", "localhost")
USER_DB_PORT = os.getenv("POSTGRES_USER_PORT", "5434")

# Set Global Env Vars so Services pick them up correctly
os.environ["POSTGRES_HOST"] = CONTENT_DB_HOST
os.environ["POSTGRES_PORT"] = CONTENT_DB_PORT
os.environ["POSTGRES_DB"] = "rag"
os.environ["POSTGRES_USER"] = "rag"
os.environ["POSTGRES_PASSWORD"] = "rag"

os.environ["POSTGRES_CONTENT_HOST"] = CONTENT_DB_HOST
os.environ["POSTGRES_CONTENT_PORT"] = CONTENT_DB_PORT

os.environ["POSTGRES_USER_HOST"] = USER_DB_HOST
os.environ["POSTGRES_USER_PORT"] = USER_DB_PORT

# --- Imports (must happen after env setup for some modules) ---
from ingest.service import IngestionService
from ingest.infra.postgres import PostgresStructureNodeRepository
from ingest.hybrid_ingestor import HybridIngestor
from app.services.profile_service import ProfileService, get_profile_service
from app.services.memory_service import MemoryService
from app.infra.artifact_db import ArtifactRepository
from app.schemas import TeacherProfile, PedagogyConfig
from app.models.artifact import Artifact
from app.rag_engine import retrieve_and_generate

def check_db_connection():
    """Checks if the databases are reachable."""
    import psycopg

    # Check Content DB
    try:
        conn_str = f"postgresql://rag:rag@{CONTENT_DB_HOST}:{CONTENT_DB_PORT}/rag"
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        print(f"✅ Connected to Content DB at {CONTENT_DB_HOST}:{CONTENT_DB_PORT}")
    except Exception as e:
        print(f"❌ Failed to connect to Content DB at {CONTENT_DB_HOST}:{CONTENT_DB_PORT}. Error: {e}")
        return False

    # Check User DB
    try:
        conn_str = f"postgresql://rag:rag@{USER_DB_HOST}:{USER_DB_PORT}/rag"
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        print(f"✅ Connected to User DB at {USER_DB_HOST}:{USER_DB_PORT}")
    except Exception as e:
        print(f"❌ Failed to connect to User DB at {USER_DB_HOST}:{USER_DB_PORT}. Error: {e}")
        return False

    return True

def ingest_book(file_path: str, book_id: uuid.UUID, category: str = "language", force: bool = False):
    """Ingests a book if it hasn't been ingested yet (or if force=True)."""
    repo = PostgresStructureNodeRepository()
    try:
        repo.ensure_schema() # Ensure table exists
    except Exception as e:
        print(f"⚠️  Schema check failed (is DB up?): {e}")
        raise

    # Check if book exists
    # This is a bit hacky since repo doesn't have "exists" method exposed easily,
    # but we can query structure_nodes.
    conn = repo.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM structure_nodes WHERE book_id = %s", (str(book_id),))
        count = cur.fetchone()[0]

    if count > 0 and not force:
        print(f"📚 Book {book_id} already exists ({count} nodes). Skipping ingestion.")
        return

    print(f"🚀 Starting Ingestion for {file_path}...")
    ingestor = HybridIngestor()

    # Should mock embedding if no API key?
    should_mock = not bool(os.getenv("OPENAI_API_KEY"))
    if should_mock:
        print("⚠️  OPENAI_API_KEY not found. Using Mock Embeddings.")

    service = IngestionService(
        structure_repo=repo,
        ingestor=ingestor,
        should_mock_embedding=should_mock
    )

    try:
        service.ingest_book(file_path, book_id=book_id, category=category)
        print("✅ Ingestion Complete.")
    except Exception as e:
        print(f"❌ Ingestion Failed: {e}")
        raise

def create_demo_profile(user_id: str, name: str, grade: str, book_id: uuid.UUID) -> TeacherProfile:
    """Creates or retrieves a demo profile."""
    service = get_profile_service()

    profile = TeacherProfile(
        user_id=user_id,
        name=name,
        grade_level=grade,
        book_list=[str(book_id)], # Link the book
        pedagogy_config=PedagogyConfig(
            tone="encouraging",
            style="interactive",
            focus_areas=["vocabulary", "speaking"]
        )
    )

    created = service.create_profile(profile)
    print(f"👤 Profile '{name}' created/updated with ID: {created.id}")
    return created

def save_demo_artifact(profile_id: str, content: str, artifact_type: str, summary: str, tags: list):
    """Saves a demo artifact."""
    repo = ArtifactRepository()
    repo.ensure_schema()
    service = MemoryService(repo=repo)

    artifact = service.save_artifact(
        profile_id=profile_id,
        content=content,
        artifact_type=artifact_type,
        summary=summary,
        topic_tags=tags
    )
    print(f"💾 Artifact saved: {artifact.title} (ID: {artifact.id})")
    return artifact

def run_rag_query(profile_id: str, book_id: uuid.UUID, query: str):
    """Runs a RAG query."""
    print(f"❓ Query: {query}")
    try:
        response = retrieve_and_generate(
            book_id=str(book_id),
            unit=1, # Default to Unit 1 for demo
            topic=query,
            profile_id=profile_id,
            use_memory=True # Enable memory for Spiral Review
        )
        print("\n🤖 Response:")
        if response and response.items:
            for item in response.items:
                print(f"- {item.stem}\n  Ans: {item.answer}\n")
        else:
             print("   (No specific items generated, possibly due to mock mode or no results)")
        return response
    except Exception as e:
        print(f"❌ RAG Failed: {e}")
        return None
