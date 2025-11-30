import os
import json
import psycopg
from typing import List, Dict, Any, Optional
from ..models import StructureNode
from ..interfaces import StructureNodeRepository
from .connection import get_connection

# Postgres Schema
POSTGRES_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Structure Nodes
CREATE TABLE IF NOT EXISTS structure_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL,
    parent_id UUID REFERENCES structure_nodes(id),
    node_level INTEGER, -- 0=Book, 1=Unit, 2=Section
    title TEXT,
    sequence_index INTEGER,
    meta_data JSONB
);

-- 2. Teacher Profiles
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
"""

class PostgresStructureNodeRepository(StructureNodeRepository):
    """Postgres implementation of StructureNodeRepository using psycopg."""

    def __init__(self, host: str = None, dbname: str = None, user: str = None, password: str = None):
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.dbname = dbname or os.getenv("POSTGRES_DB", "rag")
        self.user = user or os.getenv("POSTGRES_USER", "rag")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "rag")

    def get_connection(self) -> psycopg.Connection:
        return get_connection(self.host, self.dbname, self.user, self.password)

    def ensure_schema(self) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_SCHEMA_SQL)
            conn.commit()

    def insert_structure_nodes(self, nodes: List[StructureNode]) -> None:
        if not nodes:
            return

        query = """
        INSERT INTO structure_nodes (id, book_id, parent_id, node_level, title, sequence_index, meta_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                json.dumps(n.meta_data)
            )
            for n in nodes
        ]

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, data)
            conn.commit()

    def list_books(self, subject: str, level: Optional[int] = None, min_level: Optional[int] = None, max_level: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lists available books filtering by subject and grade level using JSONB operators.
        """
        # Base query for root nodes
        query = """
            SELECT book_id, title, meta_data
            FROM structure_nodes
            WHERE node_level = 0
            AND meta_data->>'subject' = %s
        """
        params = [subject]

        # Add level filtering
        if level is not None:
            query += " AND (meta_data->>'grade_level')::int = %s"
            params.append(level)
        elif min_level is not None and max_level is not None:
            query += " AND (meta_data->>'grade_level')::int BETWEEN %s AND %s"
            params.append(min_level)
            params.append(max_level)

        # Limit default to 20 to prevent data dump as per requirements
        query += " LIMIT 20;"

        books = []
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    books.append({
                        "book_id": str(row[0]),
                        "title": row[1],
                        "metadata": row[2]
                    })
        return books
