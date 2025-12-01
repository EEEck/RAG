import sqlite3
import json
import uuid
import math
from datetime import datetime
from typing import List, Optional, Any
from ingest.models import StructureNode
from ingest.interfaces import StructureNodeRepository
from app.models.artifact import Artifact
from app.infra.artifact_db import ArtifactRepository

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
    book_list TEXT DEFAULT '[]',
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


class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # Convert %s to ?
        query = query.replace("%s", "?")
        # Also handle NOW() -> CURRENT_TIMESTAMP
        query = query.replace("NOW()", "CURRENT_TIMESTAMP")

        if params:
             # Auto-convert list params to JSON strings for SQLite compatibility
             new_params = []
             for p in params:
                 if isinstance(p, list):
                     new_params.append(json.dumps(p))
                 else:
                     new_params.append(p)
             return self.cursor.execute(query, tuple(new_params))
        return self.cursor.execute(query)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None

        # We need description to map keys
        cols = [d[0] for d in self.cursor.description]
        return dict(zip(cols, row))

    def fetchall(self):
        rows = self.cursor.fetchall()
        cols = [d[0] for d in self.cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SQLiteConnectionWrapper:
    def __init__(self, conn, close_on_exit=True):
        self.conn = conn
        self.close_on_exit = close_on_exit

    def cursor(self, row_factory=None):
        # We ignore row_factory argument to prevent TypeError
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        if self.close_on_exit:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SQLiteTestDB:
    """
    A single SQLite database manager that can serve as a repository
    for StructureNodes, Profiles, and Artifacts during integration tests.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._shared_conn = None
        if db_path == ":memory:":
             # Use a shared connection for :memory: databases
             self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
             self._shared_conn.execute("PRAGMA foreign_keys = ON")

    def get_connection(self) -> SQLiteConnectionWrapper:
        if self._shared_conn:
            return SQLiteConnectionWrapper(self._shared_conn, close_on_exit=False)

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return SQLiteConnectionWrapper(conn, close_on_exit=True)

    def ensure_schema(self) -> None:
        # We need the raw sqlite connection or wrapper with script support?
        # SQLiteConnectionWrapper does not expose executescript.
        # But we can assume get_connection returns wrapper, and we can access .conn
        conn_wrapper = self.get_connection()
        conn = conn_wrapper.conn
        with conn:
            conn.executescript(SQLITE_STRUCTURE_NODES_SCHEMA)
            conn.executescript(SQLITE_TEACHER_PROFILES_SCHEMA)
            conn.executescript(SQLITE_ARTIFACTS_SCHEMA)
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

        # We need raw connection for executemany with ? placeholders if we used wrapper it converts %s to ?
        # But here we used ? directly.
        # So we can use raw connection.
        conn_wrapper = self.get_connection()
        with conn_wrapper.conn as conn:
            conn.executemany(query, data)
            conn.commit()

    # --- Profile Methods ---

    def insert_profile(self, id: str, user_id: str, name: str, grade_level: str, pedagogy_config: dict, content_scope: dict, book_list: List[str] = []) -> None:
        query = """
        INSERT OR REPLACE INTO teacher_profiles (id, user_id, name, grade_level, pedagogy_config, content_scope, book_list)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        data = (
            id,
            user_id,
            name,
            grade_level,
            json.dumps(pedagogy_config),
            json.dumps(content_scope),
            json.dumps(book_list)
        )
        conn_wrapper = self.get_connection()
        with conn_wrapper.conn as conn:
            conn.execute(query, data)
            conn.commit()

    def get_profile(self, profile_id: str) -> Optional[dict]:
        query = "SELECT id, user_id, name, grade_level, pedagogy_config, content_scope, book_list FROM teacher_profiles WHERE id = ?"
        conn_wrapper = self.get_connection()
        with conn_wrapper.conn as conn:
            cur = conn.execute(query, (profile_id,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "name": row[2],
                    "grade_level": row[3],
                    "pedagogy_config": json.loads(row[4]),
                    "content_scope": json.loads(row[5]),
                    "book_list": json.loads(row[6]) if row[6] else []
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
        conn_wrapper = self.get_connection()
        with conn_wrapper.conn as conn:
            conn.execute(query, data)
            conn.commit()

    def search_artifacts(self, profile_id: str, query_embedding: Optional[List[float]] = None, limit: int = 5) -> List[Artifact]:
        """
        Retrieves artifacts for a profile.
        If query_embedding is provided, performs in-memory cosine similarity sort.
        """
        query = "SELECT id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags FROM class_artifacts WHERE profile_id = ?"

        results = []
        conn_wrapper = self.get_connection()
        with conn_wrapper.conn as conn:
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

    def get_artifacts_by_date_range(self, profile_id: str, start_date: datetime, end_date: datetime, artifact_type: Optional[str] = None) -> List[Artifact]:
        """
        Retrieves artifacts for a profile within a specific date range (inclusive).
        """
        s_iso = start_date.isoformat()
        e_iso = end_date.isoformat()

        query = """
        SELECT id, profile_id, type, content, summary, created_at, embedding, related_book_ids, topic_tags
        FROM class_artifacts
        WHERE profile_id = ?
          AND created_at >= ?
          AND created_at <= ?
        """
        params = [profile_id, s_iso, e_iso]

        if artifact_type:
            query += " AND type = ?"
            params.append(artifact_type)

        query += " ORDER BY created_at DESC"

        artifacts = []
        conn_wrapper = self.get_connection()
        with conn_wrapper.conn as conn:
            cur = conn.execute(query, tuple(params))
            rows = cur.fetchall()
            for row in rows:
                # Handle created_at. It might be stored as string in SQLite
                created_at_val = row[5]
                if isinstance(created_at_val, str):
                    created_at_dt = datetime.fromisoformat(created_at_val)
                else:
                    created_at_dt = created_at_val

                artifacts.append(Artifact(
                    id=uuid.UUID(row[0]),
                    profile_id=row[1],
                    type=row[2],
                    content=row[3],
                    summary=row[4],
                    created_at=created_at_dt,
                    related_book_ids=json.loads(row[7]) if row[7] else [],
                    topic_tags=json.loads(row[8]) if row[8] else []
                ))
        return artifacts
