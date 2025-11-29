import sqlite3
import json
from typing import List
from ingest.models import StructureNode
from ingest.interfaces import StructureNodeRepository

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

class SQLiteStructureNodeRepository(StructureNodeRepository):
    """SQLite implementation of StructureNodeRepository for testing."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_schema(self) -> None:
        with self.get_connection() as conn:
            conn.executescript(SQLITE_SCHEMA_SQL)
            conn.commit()

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
