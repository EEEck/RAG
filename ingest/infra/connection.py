import os
import psycopg
from typing import Dict, Literal


def get_db_params(
    db_type: Literal["content", "user"] = "content",
) -> Dict[str, str | int]:
    if db_type == "content":
        host = os.getenv("POSTGRES_CONTENT_HOST", os.getenv("POSTGRES_HOST", "localhost"))
        port = int(os.getenv("POSTGRES_CONTENT_PORT", os.getenv("POSTGRES_PORT", "5432")))
        dbname = os.getenv("POSTGRES_CONTENT_DB", os.getenv("POSTGRES_DB", "rag"))
        user = os.getenv("POSTGRES_CONTENT_USER", os.getenv("POSTGRES_USER", "rag"))
        password = os.getenv("POSTGRES_CONTENT_PASSWORD", os.getenv("POSTGRES_PASSWORD", "rag"))
    else:
        host = os.getenv("POSTGRES_USER_HOST", os.getenv("POSTGRES_HOST", "localhost"))
        port = int(os.getenv("POSTGRES_USER_PORT", os.getenv("POSTGRES_PORT", "5432")))
        dbname = os.getenv("POSTGRES_USER_DB", os.getenv("POSTGRES_DB", "rag"))
        user = os.getenv("POSTGRES_USER_USER", os.getenv("POSTGRES_USER", "rag"))
        password = os.getenv("POSTGRES_USER_PASSWORD", os.getenv("POSTGRES_PASSWORD", "rag"))

    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }

def get_connection(
    host: str = None,
    dbname: str = None,
    user: str = None,
    password: str = None,
    port: int = None,
    db_type: Literal["content", "user"] = "content"
) -> psycopg.Connection:

    # Determine defaults based on db_type
    params = get_db_params(db_type=db_type)

    host = host or params["host"]
    dbname = dbname or params["dbname"]
    user = user or params["user"]
    password = password or params["password"]
    port = port or params["port"]

    return psycopg.connect(
        host=host,
        dbname=dbname,
        user=user,
        password=password,
        port=port,
        autocommit=False
    )
