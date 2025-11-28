from __future__ import annotations
import os
import uuid
import json
import psycopg
from typing import Dict, Any, List
from .models import StructureNode, ContentAtom

SCHEMA_SQL = """
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
"""

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        dbname=os.getenv("POSTGRES_DB", "rag"),
        user=os.getenv("POSTGRES_USER", "rag"),
        password=os.getenv("POSTGRES_PASSWORD", "rag"),
        autocommit=False
    )
    return conn

def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()

def insert_structure_nodes(conn, nodes: List[StructureNode]) -> None:
    """Batch inserts structure nodes."""
    if not nodes:
        return

    # Sort nodes by node_level to ensure parents exist before children (though DB foreign key deferral might be needed if unsorted, but usually BFS/DFS order helps.
    # Actually, standard FK constraint checks immediately.
    # StructureNode objects usually come in order from parsing (Root -> Children), so we assume list order is safe or we rely on deferred constraints if configured.
    # For now, we trust the parser order."""

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

    cur = conn.cursor()
    cur.executemany(query, data)
    conn.commit()
