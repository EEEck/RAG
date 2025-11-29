import uuid
import os
import random
from typing import List, Optional, Any
from pathlib import Path
import json

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding

from .models import StructureNode, ContentAtom
from .interfaces import StructureNodeRepository, Ingestor
from app.config import get_settings
from .classification import detect_book_category
from .infra.postgres import PostgresStructureNodeRepository

def index_atoms(
    atoms: List[ContentAtom],
    sequence_map: Optional[dict] = None,
    should_mock_embedding: bool = False,
    vector_store: Optional[Any] = None,
    storage_context: Optional[StorageContext] = None
) -> VectorStoreIndex:
    """
    Converts ContentAtoms to LlamaIndex TextNodes and persists them to the VectorStore.

    Args:
        atoms (List[ContentAtom]): List of content atoms to be indexed.
        sequence_map (Optional[dict]): Map of node_id -> sequence_index to enrich metadata.
        should_mock_embedding (bool): If True, uses a mock embedding model (for testing).
                                      Defaults to False (uses OpenAI).
        vector_store (Optional[Any]): The vector store instance to use.
                                      If None, defaults to PGVectorStore (production).
        storage_context (Optional[StorageContext]): The storage context to use.
                                                    If None, creates one from defaults.

    Returns:
        VectorStoreIndex: The created or updated index.
    """
    if not atoms:
        print("No atoms to index.")
        return None

    print("Converting atoms to LlamaIndex Nodes...")
    nodes = []
    for atom in atoms:
        # Map metadata
        # We store key identifiers in metadata for filtering/retrieval
        # atom.meta_data is now a Pydantic model

        # Serialize Pydantic metadata to dict
        meta_dict = atom.meta_data.model_dump(exclude_none=True)

        metadata = {
            "book_id": str(atom.book_id),
            "node_id": str(atom.node_id) if atom.node_id else None,
            "atom_type": atom.atom_type,
            **meta_dict
        }

        # Inject sequence_index if available
        # Ensure robust key matching by casting to string, as IDs might be UUID objects or strings
        if sequence_map and str(atom.node_id) in sequence_map:
            metadata["sequence_index"] = sequence_map[str(atom.node_id)]

        # Create a LlamaIndex TextNode
        node = TextNode(
            text=atom.content_text,
            metadata=metadata,
            id_=str(atom.id) # Ensure atom ID is preserved as node ID
        )
        nodes.append(node)

    print(f"Created {len(nodes)} nodes. Connecting to Vector Store...")

    # Setup Vector Store if not provided
    if vector_store is None and storage_context is None:
        # Default to Postgres (Production)
        vector_store = PGVectorStore.from_params(
            database=os.getenv("POSTGRES_DB", "rag"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            password=os.getenv("POSTGRES_PASSWORD", "rag"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER", "rag"),
            table_name="content_atoms",
            embed_dim=1536
        )

    # Use provided storage_context or create new one
    if storage_context is None:
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

    # Build Index (This pushes to DB/StorageContext)
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model
    )
    print("Success! Atoms Indexed into Vector Store.")
    return index

def run_ingestion(
    file_path: str,
    book_id: Optional[uuid.UUID] = None,
    should_mock_embedding: bool = False,
    category: Optional[str] = None,
    structure_repo: Optional[StructureNodeRepository] = None,
    ingestor: Optional[Ingestor] = None,
    vector_store: Optional[Any] = None,
    storage_context: Optional[StorageContext] = None
) -> None:
    """
    Runs the full ingestion pipeline for a given document.

    Args:
        file_path (str): Path to the source file.
        book_id (Optional[uuid.UUID]): Unique identifier for the book.
        should_mock_embedding (bool): Whether to use mock embeddings.
        category (Optional[str]): Book category.
        structure_repo (Optional[StructureNodeRepository]): Repo for structure nodes. Defaults to Postgres.
        ingestor (Optional[Ingestor]): Ingestion strategy. Defaults to HybridIngestor.
        vector_store (Optional[Any]): Custom vector store instance.
        storage_context (Optional[StorageContext]): Custom storage context.
    """

    if book_id is None:
        book_id = uuid.uuid4()

    # Default to Postgres Repository if none provided
    if structure_repo is None:
        structure_repo = PostgresStructureNodeRepository()

    # Default to HybridIngestor if none provided
    if ingestor is None:
        # Import HybridIngestor locally to avoid top-level import errors if docling is missing
        try:
            from .hybrid_ingestor import HybridIngestor
            ingestor = HybridIngestor()
        except ImportError as e:
            print(f"Error importing HybridIngestor: {e}")
            print("Ingestion cannot proceed without docling.")
            return

    print(f"--- Starting Ingestion for Book ID: {book_id} ---")
    print(f"Source: {file_path}")

    # 1. Parse Document
    nodes = []
    atoms = []

    if str(file_path).endswith(".json"):
        print("Detected JSON input. Loading directly...")
        with open(file_path, "r") as f:
            data = json.load(f)

        if category is None:
             texts = data.get("texts", [])
             sample_text = "\n".join([t.get("text", "") for t in texts[:5]])
             category = detect_book_category(os.path.basename(file_path), sample_text)

        nodes, atoms = ingestor._parse_docling_structure(data, book_id, file_path, category)
    else:
        nodes, atoms = ingestor.ingest_book(str(file_path), book_id, category)

    print(f"Parsed {len(nodes)} structure nodes and {len(atoms)} content atoms.")

    # 2. Persist Structure Nodes (Manual DB)
    print(f"Using repository: {structure_repo.__class__.__name__} for structure nodes...")

    try:
        # Ensure schema exists
        structure_repo.ensure_schema()

        print("Inserting structure nodes...")
        structure_repo.insert_structure_nodes(nodes)
    except Exception as e:
        print(f"Error during structure node insertion: {e}")
        raise

    # 3. Enrich & Persist Content Atoms (Vector Store)
    try:
        sequence_map = {str(n.id): n.sequence_index for n in nodes}
        index_atoms(
            atoms,
            sequence_map=sequence_map,
            should_mock_embedding=should_mock_embedding,
            vector_store=vector_store,
            storage_context=storage_context
        )
    except Exception as e:
        print(f"Error during Vector Index indexing: {e}")
        raise

    # 4. Trigger Async Vision Enrichment (Only for Postgres/Prod usually)
    # We detect if we are using the Postgres repo to decide if we should trigger Celery
    if isinstance(structure_repo, PostgresStructureNodeRepository):
        try:
            from app.celery_worker import enrich_images_task
            print("Triggering vision enrichment task...")
            enrich_images_task.delay(batch_size=50)
        except ImportError:
            print("Warning: app.celery_worker not found. Vision enrichment skipped (async).")
        except Exception as e:
            print(f"Warning: Failed to trigger vision enrichment: {e}")
    else:
        print("Skipping async vision enrichment in non-postgres mode.")

    print("Ingestion complete.")

if __name__ == "__main__":
    pass
