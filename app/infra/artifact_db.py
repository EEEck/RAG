import json
from datetime import datetime
from typing import List, Optional
import psycopg
from app.db import get_conn
from app.models.artifact import Artifact

# Schema for Artifacts
ARTIFACTS_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS class_artifacts (
    id UUID PRIMARY KEY,
    profile_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    embedding vector(1536), -- Assuming OpenAI embeddings
    related_book_ids JSONB,
    topic_tags JSONB
);

CREATE INDEX IF NOT EXISTS idx_class_artifacts_profile_id ON class_artifacts(profile_id);
"""

class ArtifactRepository:
    """
    Repository for managing User Artifacts in Postgres.
    Uses app.db.get_conn() which handles connection parameters and pgvector registration.
    """

    def ensure_schema(self) -> None:
        """Ensures the artifacts table exists."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(ARTIFACTS_SCHEMA_SQL)
            conn.commit()

    def save_artifact(self, artifact: Artifact) -> None:
        """Saves an artifact to the database."""
        query = """
        INSERT INTO class_artifacts (id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            content = EXCLUDED.content,
            summary = EXCLUDED.summary,
            embedding = EXCLUDED.embedding;
        """

        # NOTE: psycopg with register_vector handles List[float] -> vector automatically
        data = (
            artifact.id,
            artifact.profile_id,
            artifact.type,
            artifact.content,
            artifact.summary,
            artifact.created_at,
            artifact.embedding,
            json.dumps(artifact.related_book_ids),
            json.dumps(artifact.topic_tags)
        )

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, data)
            conn.commit()

    def search_artifacts(self, profile_id: str, query_embedding: Optional[List[float]] = None, limit: int = 5) -> List[Artifact]:
        """
        Search artifacts by profile_id and optionally by vector similarity.
        """
        if query_embedding:
            # Hybrid search: Match profile AND order by vector similarity
            # Using <=> operator for cosine distance (pgvector)
            query = """
            SELECT id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags
            FROM class_artifacts
            WHERE profile_id = %s
            ORDER BY embedding <=> %s
            LIMIT %s;
            """
            params = (profile_id, query_embedding, limit)
        else:
            # Just retrieve latest
            query = """
            SELECT id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags
            FROM class_artifacts
            WHERE profile_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
            """
            params = (profile_id, limit)

        artifacts = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    artifacts.append(Artifact(
                        id=row[0],
                        profile_id=row[1],
                        type=row[2],
                        content=row[3],
                        summary=row[4],
                        created_at=row[5],
                        # embedding=row[6], # Skip loading embedding back
                        related_book_ids=row[7],
                        topic_tags=row[8]
                    ))
        return artifacts

    def get_artifacts_by_date_range(self, profile_id: str, start_date: datetime, end_date: datetime, artifact_type: Optional[str] = None) -> List[Artifact]:
        """
        Retrieves artifacts for a profile within a specific date range (inclusive).
        """
        query = """
        SELECT id, profile_id, type, content, summary, created_at, related_book_ids, topic_tags
        FROM class_artifacts
        WHERE profile_id = %s
          AND created_at >= %s
          AND created_at <= %s
        """
        params = [profile_id, start_date, end_date]

        if artifact_type:
            query += " AND type = %s"
            params.append(artifact_type)

        query += " ORDER BY created_at DESC;"

        artifacts = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                for row in rows:
                    artifacts.append(Artifact(
                        id=row[0],
                        profile_id=row[1],
                        type=row[2],
                        content=row[3],
                        summary=row[4],
                        created_at=row[5],
                        embedding=None, # Explicitly none to avoid fetching large vectors
                        related_book_ids=row[6],
                        topic_tags=row[7]
                    ))
        return artifacts
