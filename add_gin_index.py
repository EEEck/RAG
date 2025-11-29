import os
from dotenv import load_dotenv

load_dotenv()

def add_gin_index():
    dsn = f"postgresql://{os.getenv('POSTGRES_USER', 'rag')}:{os.getenv('POSTGRES_PASSWORD', 'rag')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'rag')}"

    # Try importing psycopg (v3) first, then fallback to psycopg2
    try:
        import psycopg
        connector = psycopg
        print("Using psycopg (v3)")
    except ImportError:
        try:
            import psycopg2 as connector
            print("Using psycopg2")
        except ImportError:
            print("Error: Neither psycopg nor psycopg2 is installed.")
            return

    # Tables to check: LlamaIndex often prefixes with 'data_'
    target_tables = ["data_content_atoms", "content_atoms"]

    conn = None
    try:
        conn = connector.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor()

        found_table = None
        for table in target_tables:
            # Check table existence (Postgres specific)
            cur.execute("SELECT to_regclass(%s)", (table,))
            result = cur.fetchone()
            if result and result[0] is not None:
                found_table = table
                break

        if not found_table:
            print(f"No content atoms table found. Checked: {target_tables}")
            return

        print(f"Found table: {found_table}")

        index_name = f"idx_{found_table}_meta_gin"
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {found_table} USING GIN (metadata_)"

        print(f"Executing: {query}")
        cur.execute(query)
        print("GIN Index created successfully.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_gin_index()
