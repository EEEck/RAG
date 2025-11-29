from __future__ import annotations
import os
import uuid
import json
import psycopg
import sqlite3
from typing import Dict, Any, List, Union
from .models import StructureNode, ContentAtom

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
"""

# SQLite Schema
SQLITE_SCHEMA_SQL = """
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

def get_db_connection(mode: str = "postgres", **kwargs) -> Union[psycopg.Connection, sqlite3.Connection]:
    """
    Establishes a connection to the database.

    Args:
        mode (str): "postgres" or "sqlite".
        **kwargs: Additional arguments for connection (e.g. db_path for sqlite).
    """
    if mode == "sqlite":
        db_path = kwargs.get("db_path", ":memory:")
        conn = sqlite3.connect(db_path)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # Default to Postgres
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
    if isinstance(conn, sqlite3.Connection):
        cur.executescript(SQLITE_SCHEMA_SQL)
    else:
        cur.execute(POSTGRES_SCHEMA_SQL)
    conn.commit()

def insert_structure_nodes(conn, nodes: List[StructureNode]) -> None:
    """Batch inserts structure nodes."""
    if not nodes:
        return

    is_sqlite = isinstance(conn, sqlite3.Connection)

    if is_sqlite:
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
    else:
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
