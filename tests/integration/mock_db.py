from __future__ import annotations
import os
import json
import sqlite3
from typing import List, Any
from ingest.models import StructureNode

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

def get_db_connection(**kwargs) -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    # Tests will pass db_path via kwargs or we rely on patching
    # However, ingest.pipeline calls get_db_connection() with NO args usually.
    # We need a way to set the DB path for the mock.
    # We can use an env var or a module-level variable in this mock module.

    db_path = kwargs.get("db_path")
    if not db_path:
        db_path = os.environ.get("TEST_SQLITE_DB_PATH", ":memory:")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.executescript(SQLITE_SCHEMA_SQL)
    conn.commit()

def insert_structure_nodes(conn, nodes: List[StructureNode]) -> None:
    """Batch inserts structure nodes (SQLite version)."""
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

    cur = conn.cursor()
    cur.executemany(query, data)
    conn.commit()
