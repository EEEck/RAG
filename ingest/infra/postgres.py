import os
import json
import psycopg
from typing import List, Dict, Any, Optional
from ..models import StructureNode
from ..interfaces import StructureNodeRepository
from .connection import get_connection

# Postgres Schema - Content DB
CONTENT_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Structure Nodes
CREATE TABLE IF NOT EXISTS structure_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL,
    parent_id UUID REFERENCES structure_nodes(id),
    node_level INTEGER, -- 0=Book, 1=Unit, 2=Section
    title TEXT,
    sequence_index INTEGER,
    meta_data JSONB,
    owner_id TEXT -- NULL for global, user_id for private
);

CREATE INDEX IF NOT EXISTS idx_structure_nodes_owner ON structure_nodes(owner_id);

-- Pedagogy Strategies (Global + User Extensions)
-- Added owner_id for future user-specific logic
CREATE TABLE IF NOT EXISTS pedagogy_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id TEXT, -- NULL for global, user_id for private
    content TEXT,
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

# Postgres Schema - User DB
USER_SCHEMA_SQL = """
-- 1. Teacher Profiles
CREATE TABLE IF NOT EXISTS teacher_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    grade_level TEXT,
    pedagogy_config JSONB DEFAULT '{}',
    content_scope JSONB DEFAULT '{}',
    book_list TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Class Artifacts (Memory)
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

class PostgresStructureNodeRepository(StructureNodeRepository):
    """Postgres implementation of StructureNodeRepository using psycopg."""

    def __init__(self, host: str = None, dbname: str = None, user: str = None, password: str = None):
        self.host = host # Rely on connection.py defaults usually
        self.dbname = dbname
        self.user = user
        self.password = password

    def get_connection(self) -> psycopg.Connection:
        # Use content DB
        return get_connection(self.host, self.dbname, self.user, self.password, db_type="content")

    def ensure_schema(self) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CONTENT_SCHEMA_SQL)
            conn.commit()

    def insert_structure_nodes(self, nodes: List[StructureNode]) -> None:
        if not nodes:
            return

        query = """
        INSERT INTO structure_nodes (id, book_id, parent_id, node_level, title, sequence_index, meta_data, owner_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
        """
        data = [
            (
                n.id,
                n.book_id,
                n.parent_id,
                n.node_level,
                n.title,
                n.sequence_index,
                json.dumps(n.meta_data),
                n.owner_id
            )
            for n in nodes
        ]

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, data)
            conn.commit()

    def list_books(self, subject: str, title: Optional[str] = None, level: Optional[int] = None, min_level: Optional[int] = None, max_level: Optional[int] = None, excluded_subjects: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lists available books filtering by subject and grade level.

        Args:
            subject: The subject to filter by. If 'other', looks for subjects NOT in excluded_subjects.
            title: Optional title search. Uses fuzzy matching (pg_trgm) and partial match (ILIKE).
            excluded_subjects: List of subjects to exclude when searching for 'other'.
        """
        # Base query for root nodes
        query = """
            SELECT book_id, title, meta_data
            FROM structure_nodes
            WHERE node_level = 0
        """
        params = []

        # Subject Logic
        if subject.lower() == 'other' and excluded_subjects:
            query += " AND (meta_data->>'subject') != ALL(%s)"
            params.append(excluded_subjects)
        else:
            query += " AND meta_data->>'subject' = %s"
            params.append(subject)

        # Title Logic (Fuzzy + Partial)
        if title:
            # Combined check:
            # 1. ILIKE for standard partial matches (e.g. "Math" matches "Math 1")
            # 2. % operator (pg_trgm) for fuzzy/typo matches (e.g. "Mth" matches "Math 1")
            # Note: We assume pg_trgm extension is enabled.
            query += " AND (title ILIKE %s OR title % %s)"
            params.append(f"%{title}%")
            params.append(title)

        # Add level filtering
        if level is not None:
            query += " AND (meta_data->>'grade_level')::int = %s"
            params.append(level)
        elif min_level is not None and max_level is not None:
            query += " AND (meta_data->>'grade_level')::int BETWEEN %s AND %s"
            params.append(min_level)
            params.append(max_level)

        # Limit default to 20
        query += " LIMIT 20;"

        books = []
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Set similarity threshold for this session to be strict enough but allow typos
                # Default is 0.3, maybe set to 0.2? 0.3 is usually fine.
                # cur.execute("SELECT set_limit(0.3);")

                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    books.append({
                        "book_id": str(row[0]),
                        "title": row[1],
                        "metadata": row[2]
                    })
        return books

class PostgresUserRepository:
    """Helper to manage User DB Schema."""

    def ensure_schema(self) -> None:
        # Use user DB
        with get_connection(db_type="user") as conn:
            with conn.cursor() as cur:
                cur.execute(USER_SCHEMA_SQL)
            conn.commit()
