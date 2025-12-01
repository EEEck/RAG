from __future__ import annotations
from typing import Literal

import psycopg
from pgvector.psycopg import register_vector

from .config import get_settings


def get_conn(db_type: Literal["content", "user"] = "content") -> psycopg.Connection:
    settings = get_settings()
    if db_type == "content":
        dsn = settings.pg_content_dsn
    else:
        dsn = settings.pg_user_dsn

    conn = psycopg.connect(dsn)
    # Register vector type (needed for both if they store vectors)
    # Artifacts (User DB) stores vectors. Content (Content DB) stores vectors.
    register_vector(conn)
    return conn
