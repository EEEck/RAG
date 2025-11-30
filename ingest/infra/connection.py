import os
import psycopg

def get_connection(host: str = None, dbname: str = None, user: str = None, password: str = None) -> psycopg.Connection:
    host = host or os.getenv("POSTGRES_HOST", "localhost")
    dbname = dbname or os.getenv("POSTGRES_DB", "rag")
    user = user or os.getenv("POSTGRES_USER", "rag")
    password = password or os.getenv("POSTGRES_PASSWORD", "rag")

    return psycopg.connect(
        host=host,
        dbname=dbname,
        user=user,
        password=password,
        autocommit=False
    )
