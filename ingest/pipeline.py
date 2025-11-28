import uuid
import os
import random
from typing import List, Optional
from pathlib import Path
import json

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding

from .hybrid_ingestor import HybridIngestor
from .models import StructureNode, ContentAtom
from . import db
from app.config import get_settings

def index_atoms_to_postgres(atoms: List[ContentAtom], should_mock_embedding: bool = False):
    """
    Converts ContentAtoms to LlamaIndex TextNodes and persists them to Postgres via PGVectorStore.

    Args:
        atoms (List[ContentAtom]): List of content atoms to be indexed.
        should_mock_embedding (bool): If True, uses a mock embedding model (for testing).
                                      Defaults to False (uses OpenAI).
    """
    if not atoms:
        print("No atoms to index.")
        return

    print("Converting atoms to LlamaIndex Nodes...")
    nodes = []
    for atom in atoms:
        # Map metadata
        # We store key identifiers in metadata for filtering/retrieval
        metadata = {
            "book_id": str(atom.book_id),
            "node_id": str(atom.node_id) if atom.node_id else None,
            "atom_type": atom.atom_type,
            **atom.meta_data
        }

        # Create a LlamaIndex TextNode
        node = TextNode(
            text=atom.content_text,
            metadata=metadata
        )
        nodes.append(node)

    print(f"Created {len(nodes)} nodes. Connecting to Postgres (LlamaIndex)...")

    # Setup Vector Store
    # Uses environment variables for connection or defaults, matching db.py
    vector_store = PGVectorStore.from_params(
        database=os.getenv("POSTGRES_DB", "rag"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        password=os.getenv("POSTGRES_PASSWORD", "rag"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "rag"),
        table_name="content_atoms",
        embed_dim=1536
    )

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Setup Embedding Model
    if should_mock_embedding:
        print("Using Mock Embeddings...")
        embed_model = MockEmbedding(embed_dim=1536)
    else:
        print("Using OpenAI Embeddings...")
        embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

    # Build Index (This pushes to DB)
    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model
    )
    print("Success! Atoms Indexed into Postgres.")

def run_ingestion(
    file_path: str,
    book_id: Optional[uuid.UUID] = None,
    should_mock_embedding: bool = False
) -> None:
    """
    Runs the full ingestion pipeline for a given document.

    This process involves:
    1. Parsing the document using `HybridIngestor`.
    2. Persisting structure nodes to the Relational DB.
    3. Generating embeddings and persisting content atoms to the Vector DB.

    Args:
        file_path (str): Path to the source file (PDF, JSON, etc.).
        book_id (Optional[uuid.UUID]): Unique identifier for the book. Generated if not provided.
        should_mock_embedding (bool): Whether to use mock embeddings. Defaults to False.

    Raises:
        Exception: If any step of the ingestion process fails.
    """
    if book_id is None:
        book_id = uuid.uuid4()

    print(f"--- Starting Ingestion for Book ID: {book_id} ---")
    print(f"Source: {file_path}")

    # 1. Parse Document
    ingestor = HybridIngestor()
    nodes = []
    atoms = []

    if str(file_path).endswith(".json"):
        print("Detected JSON input. Loading directly...")
        with open(file_path, "r") as f:
            data = json.load(f)
        nodes, atoms = ingestor._parse_docling_structure(data, book_id)
    else:
        nodes, atoms = ingestor.ingest_book(str(file_path), book_id)

    print(f"Parsed {len(nodes)} structure nodes and {len(atoms)} content atoms.")

    # 2. Persist Structure Nodes (Manual DB)
    print("Connecting to DB for structure nodes...")
    conn = db.get_db_connection()
    try:
        # Ensure schema exists (creates structure_nodes table if missing)
        db.ensure_schema(conn)

        print("Inserting structure nodes...")
        db.insert_structure_nodes(conn, nodes)
    except Exception as e:
        print(f"Error during structure node insertion: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    # 3. Enrich & Persist Content Atoms (LlamaIndex)
    try:
        index_atoms_to_postgres(atoms, should_mock_embedding)
    except Exception as e:
        print(f"Error during LlamaIndex indexing: {e}")
        raise

    print("Ingestion complete.")

if __name__ == "__main__":
    pass
