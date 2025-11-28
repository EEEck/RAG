from __future__ import annotations
import os
import uuid
import json
import psycopg
from typing import Dict, Any, List
from .models import StructureNode, ContentAtom

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop old tables if they exist (clean slate for dev)
DROP TABLE IF EXISTS vocab_entry;
DROP TABLE IF EXISTS lesson;
DROP TABLE IF EXISTS textbook;

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

-- 2. Content Atoms (Partitioned Parent Table)
CREATE TABLE IF NOT EXISTS content_atoms (
    id UUID DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL,
    node_id UUID REFERENCES structure_nodes(id),
    atom_type VARCHAR(50), -- 'text', 'image_desc', 'equation_latex', 'vocab_card'
    content_text TEXT,
    embedding vector(1536), -- OpenAI Dimension
    meta_data JSONB,
    PRIMARY KEY (id, book_id)
) PARTITION BY LIST (book_id);

-- 3. Function to Auto-Create Partitions
CREATE OR REPLACE FUNCTION create_book_partition(new_book_id UUID)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
BEGIN
    partition_name := 'content_book_' || replace(new_book_id::text, '-', '_');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF content_atoms FOR VALUES IN (%L)',
        partition_name, new_book_id
    );
    EXECUTE format(
        'CREATE INDEX ON %I USING hnsw (embedding vector_cosine_ops)',
        partition_name
    );
END;
$$ LANGUAGE plpgsql;
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

def create_partition(conn, book_id: uuid.UUID) -> None:
    cur = conn.cursor()
    cur.execute("SELECT create_book_partition(%s)", (book_id,))
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

def insert_content_atoms(conn, atoms: List[ContentAtom]) -> None:
    """Batch inserts content atoms."""
    if not atoms:
        return

    query = """
    INSERT INTO content_atoms (id, book_id, node_id, atom_type, content_text, embedding, meta_data)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id, book_id) DO NOTHING;
    """

    data = [
        (
            a.id,
            a.book_id,
            a.node_id,
            a.atom_type,
            a.content_text,
            a.embedding, # psycopg handles list -> vector if pgvector installed or registered. Will test.
            json.dumps(a.meta_data)
        )
        for a in atoms
    ]

    cur = conn.cursor()
    cur.executemany(query, data)
    conn.commit()
