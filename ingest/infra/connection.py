import os
import psycopg
from typing import Literal

def get_connection(
    host: str = None,
    dbname: str = None,
    user: str = None,
    password: str = None,
    db_type: Literal["content", "user"] = "content"
) -> psycopg.Connection:

    # Determine defaults based on db_type
    if db_type == "content":
        default_host = os.getenv("POSTGRES_CONTENT_HOST", os.getenv("POSTGRES_HOST", "localhost"))
        default_db = os.getenv("POSTGRES_CONTENT_DB", os.getenv("POSTGRES_DB", "rag"))
        default_user = os.getenv("POSTGRES_CONTENT_USER", os.getenv("POSTGRES_USER", "rag"))
        default_pass = os.getenv("POSTGRES_CONTENT_PASSWORD", os.getenv("POSTGRES_PASSWORD", "rag"))
    else: # user
        default_host = os.getenv("POSTGRES_USER_HOST", os.getenv("POSTGRES_HOST", "localhost"))
        default_db = os.getenv("POSTGRES_USER_DB", os.getenv("POSTGRES_DB", "rag"))
        default_user = os.getenv("POSTGRES_USER_USER", os.getenv("POSTGRES_USER", "rag"))
        default_pass = os.getenv("POSTGRES_USER_PASSWORD", os.getenv("POSTGRES_PASSWORD", "rag"))

    host = host or default_host
    dbname = dbname or default_db
    user = user or default_user
    password = password or default_pass

    return psycopg.connect(
        host=host,
        dbname=dbname,
        user=user,
        password=password,
        autocommit=False
    )
