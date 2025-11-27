from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector

from .config import get_settings


def get_conn() -> psycopg.Connection:
    settings = get_settings()
    conn = psycopg.connect(settings.pg_dsn)
    register_vector(conn)
    return conn
