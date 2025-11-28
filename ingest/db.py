from __future__ import annotations
import uuid
from typing import Dict, Any, List

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop old tables if they exist
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


def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()


def create_partition(conn, book_id: uuid.UUID) -> None:
    cur = conn.cursor()
    cur.execute("SELECT create_book_partition(%s)", (book_id,))
    conn.commit()
