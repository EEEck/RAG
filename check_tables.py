import psycopg
import os
import sys

try:
    import fitz
    print("PyMuPDF (fitz) is installed.")
except ImportError:
    print("PyMuPDF (fitz) is NOT installed.")

try:
    import openai
    print("openai is installed.")
except ImportError:
    print("openai is NOT installed.")

def check_tables():
    try:
        conn = psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            dbname=os.getenv("POSTGRES_DB", "rag"),
            user=os.getenv("POSTGRES_USER", "rag"),
            password=os.getenv("POSTGRES_PASSWORD", "rag")
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        print("Tables in public schema:", [t[0] for t in tables])

        # Check columns of data_content_atoms if it exists
        if ('data_content_atoms',) in tables:
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'data_content_atoms'")
            columns = cur.fetchall()
            print("Columns in data_content_atoms:", columns)

    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    check_tables()
