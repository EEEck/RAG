import uuid
import os
import random
from typing import List, Optional
from pathlib import Path

from .hybrid_ingestor import HybridIngestor
from .models import StructureNode, ContentAtom
from . import db

def mock_embedding(text: str) -> List[float]:
    """Generates a random 1536-dim vector for testing."""
    # Deterministic random based on text length to have repeatable results in dev
    random.seed(len(text))
    return [random.random() for _ in range(1536)]

def run_ingestion(
    file_path: str,
    book_id: Optional[uuid.UUID] = None,
    should_mock_embedding: bool = True
) -> None:
    """
    Runs the full ingestion pipeline for a given document.
    """
    if book_id is None:
        book_id = uuid.uuid4()

    print(f"--- Starting Ingestion for Book ID: {book_id} ---")
    print(f"Source: {file_path}")

    # 1. Parse Document
    ingestor = HybridIngestor()
    # If file_path ends in json, we might want to bypass ingest_book which calls docling.convert
    # But HybridIngestor.ingest_book expects a file path.
    # We'll need to modify HybridIngestor or handle JSON loading here if we want to support direct JSON injection
    # For now, let's assume the ingestor can handle it or we use the _parse_docling_structure directly if JSON.

    nodes = []
    atoms = []

    if str(file_path).endswith(".json"):
        import json
        print("Detected JSON input. Loading directly...")
        with open(file_path, "r") as f:
            data = json.load(f)
        # We access the internal method for this test/dev scenario
        nodes, atoms = ingestor._parse_docling_structure(data, book_id)
    else:
        nodes, atoms = ingestor.ingest_book(str(file_path), book_id)

    print(f"Parsed {len(nodes)} structure nodes and {len(atoms)} content atoms.")

    # 2. Enrich (Embeddings)
    # TODO: Integrate real embedding call here
    if should_mock_embedding:
        print("Generating mock embeddings...")
        for atom in atoms:
            atom.embedding = mock_embedding(atom.content_text)

    # 3. Persist
    print("Connecting to DB...")
    conn = db.get_db_connection()
    try:
        # Ensure partition exists
        print(f"Creating partition for book {book_id}...")
        db.create_partition(conn, book_id)

        print("Inserting structure nodes...")
        db.insert_structure_nodes(conn, nodes)

        print("Inserting content atoms...")
        db.insert_content_atoms(conn, atoms)

        print("Ingestion complete.")
    except Exception as e:
        print(f"Error during DB operations: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Example usage
    # run_ingestion("data/toy_green_line_1_docling.json")
    pass
