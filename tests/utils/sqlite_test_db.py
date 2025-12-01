import sqlite3
import json
import uuid
import math
from typing import List, Optional, Any
from ingest.models import StructureNode
from ingest.interfaces import StructureNodeRepository
from app.models.artifact import Artifact
from app.infra.artifact_db import ArtifactRepository
from app.schemas import PedagogyStrategy

# --- Schemas ---

SQLITE_STRUCTURE_NODES_SCHEMA = """
CREATE TABLE IF NOT EXISTS structure_nodes (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,
    parent_id TEXT REFERENCES structure_nodes(id),
    node_level INTEGER,
    title TEXT,
    sequence_index INTEGER,
    meta_data TEXT
);
"""

SQLITE_TEACHER_PROFILES_SCHEMA = """
CREATE TABLE IF NOT EXISTS teacher_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    grade_level TEXT,
    pedagogy_config TEXT DEFAULT '{}',
    content_scope TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SQLITE_ARTIFACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS class_artifacts (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMP,
    embedding TEXT,
    related_book_ids TEXT,
    topic_tags TEXT
);
"""

SQLITE_PEDAGOGY_SCHEMA = """
CREATE TABLE IF NOT EXISTS pedagogy_strategies (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subject TEXT,
    min_grade INTEGER DEFAULT 0,
    max_grade INTEGER DEFAULT 12,
    institution_type TEXT,
    prompt_injection TEXT,
    embedding TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# --- Helpers ---

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SQLiteTestDB:
    """
    A single SQLite database manager that can serve as a repository
    for StructureNodes, Profiles, Artifacts, and Pedagogy during integration tests.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_schema(self) -> None:
        with self.get_connection() as conn:
            conn.executescript(SQLITE_STRUCTURE_NODES_SCHEMA)
            conn.executescript(SQLITE_TEACHER_PROFILES_SCHEMA)
            conn.executescript(SQLITE_ARTIFACTS_SCHEMA)
            conn.executescript(SQLITE_PEDAGOGY_SCHEMA)
            conn.commit()

    # --- Structure Node Methods ---

    def insert_structure_nodes(self, nodes: List[StructureNode]) -> None:
        if not nodes:
            return
        query = """
        INSERT OR IGNORE INTO structure_nodes (id, book_id, parent_id, node_level, title, sequence_index, meta_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                str(n.id),
                str(n.book_id),
                str(n.parent_id) if n.parent_id else None,
                n.node_level,
                n.title,
                n.sequence_index,
                json.dumps(n.meta_data)
            )
            for n in nodes
        ]
        with self.get_connection() as conn:
            conn.executemany(query, data)
            conn.commit()

    # --- Profile Methods ---

    def insert_profile(self, id: str, user_id: str, name: str, grade_level: str, pedagogy_config: dict, content_scope: dict) -> None:
        query = """
        INSERT OR REPLACE INTO teacher_profiles (id, user_id, name, grade_level, pedagogy_config, content_scope)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        data = (
            id,
            user_id,
            name,
            grade_level,
            json.dumps(pedagogy_config),
            json.dumps(content_scope)
        )
        with self.get_connection() as conn:
            conn.execute(query, data)
            conn.commit()

    def get_profile(self, profile_id: str) -> Optional[dict]:
        query = "SELECT id, user_id, name, grade_level, pedagogy_config, content_scope FROM teacher_profiles WHERE id = ?"
        with self.get_connection() as conn:
            cur = conn.execute(query, (profile_id,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "name": row[2],
                    "grade_level": row[3],
                    "pedagogy_config": json.loads(row[4]),
                    "content_scope": json.loads(row[5])
                }
        return None

    # --- Artifact Methods (Mimicking ArtifactRepository) ---

    def save_artifact(self, artifact: Artifact) -> None:
        query = """
        INSERT OR REPLACE INTO class_artifacts (id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = (
            str(artifact.id),
            artifact.profile_id,
            artifact.type,
            artifact.content,
            artifact.summary,
            artifact.created_at.isoformat() if artifact.created_at else None,
            json.dumps(artifact.embedding) if artifact.embedding else None,
            json.dumps(artifact.related_book_ids),
            json.dumps(artifact.topic_tags)
        )
        with self.get_connection() as conn:
            conn.execute(query, data)
            conn.commit()

    def search_artifacts(self, profile_id: str, query_embedding: Optional[List[float]] = None, limit: int = 5) -> List[Artifact]:
        """
        Retrieves artifacts for a profile.
        If query_embedding is provided, performs in-memory cosine similarity sort.
        """
        query = "SELECT id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags FROM class_artifacts WHERE profile_id = ?"

        results = []
        with self.get_connection() as conn:
            cur = conn.execute(query, (profile_id,))
            rows = cur.fetchall()

            for row in rows:
                emb_json = row[6]
                emb = json.loads(emb_json) if emb_json else None

                # Reconstruct Artifact object
                # Note: Created_at handling might need robust parsing if generic ISO string
                art = Artifact(
                    id=uuid.UUID(row[0]),
                    profile_id=row[1],
                    type=row[2],
                    content=row[3],
                    summary=row[4],
                    created_at=row[5], # Pydantic might auto-parse this from ISO string
                    # embedding=emb, # We typically don't return embedding in search results unless needed
                    related_book_ids=json.loads(row[7]) if row[7] else [],
                    topic_tags=json.loads(row[8]) if row[8] else []
                )

                # Store tuple (similarity, artifact)
                sim = 0.0
                if query_embedding and emb:
                    sim = cosine_similarity(query_embedding, emb)

                results.append((sim, art))

        if query_embedding:
            # Sort by similarity desc
            results.sort(key=lambda x: x[0], reverse=True)
        else:
            # Sort by created_at desc (if available) - naive sort
            # results.sort(key=lambda x: x[1].created_at or "", reverse=True)
            pass

        # Return just the artifacts, limited
        return [r[1] for r in results[:limit]]

    # --- Pedagogy Methods (Mimicking PedagogyService DB Logic) ---

    def insert_pedagogy_strategy(self, strategy: PedagogyStrategy, embedding: List[float]) -> None:
        query = """
        INSERT OR REPLACE INTO pedagogy_strategies (
            id, title, subject, min_grade, max_grade, institution_type, prompt_injection, embedding
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        injection_json = json.dumps(strategy.prompt_injection) if isinstance(strategy.prompt_injection, (dict, list)) else json.dumps(strategy.prompt_injection)

        data = (
            strategy.id,
            strategy.title,
            strategy.subject,
            strategy.min_grade,
            strategy.max_grade,
            strategy.institution_type,
            injection_json,
            json.dumps(embedding)
        )

        with self.get_connection() as conn:
            conn.execute(query, data)
            conn.commit()

    def search_pedagogy_strategies(self, query_embedding: List[float], subject: Optional[str] = None, grade: Optional[int] = None, limit: int = 3) -> List[PedagogyStrategy]:
        """
        Searches strategies with in-memory vector similarity.
        """
        sql = "SELECT id, title, subject, min_grade, max_grade, institution_type, prompt_injection, embedding FROM pedagogy_strategies WHERE 1=1"
        params = []

        if subject:
            sql += " AND subject = ?"
            params.append(subject)

        if grade is not None:
            sql += " AND min_grade <= ? AND max_grade >= ?"
            params.append(grade)
            params.append(grade)

        results = []
        with self.get_connection() as conn:
            cur = conn.execute(sql, tuple(params))
            rows = cur.fetchall()

            for row in rows:
                emb = json.loads(row[7]) if row[7] else []

                # Deserialization of prompt_injection
                prompt_injection = row[6]
                try:
                    prompt_injection = json.loads(prompt_injection)
                except:
                    pass

                strategy = PedagogyStrategy(
                    id=row[0],
                    title=row[1],
                    subject=row[2],
                    min_grade=row[3],
                    max_grade=row[4],
                    institution_type=row[5],
                    prompt_injection=prompt_injection,
                    summary_for_search="" # Not stored separately in this mock, could be inferred
                )

                sim = cosine_similarity(query_embedding, emb) if query_embedding and emb else 0.0
                results.append((sim, strategy))

        # Sort by similarity
        results.sort(key=lambda x: x[0], reverse=True)

        return [r[1] for r in results[:limit]]
