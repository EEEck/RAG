import uuid
import os
import json
from typing import List, Optional, Any, Tuple
from pathlib import Path

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.embeddings import MockEmbedding

from .models import StructureNode, ContentAtom
from .interfaces import StructureNodeRepository, Ingestor
from .classification import detect_book_category

class IngestionService:
    """
    Orchestrates the ingestion of a book: Parsing -> Persisting Structure -> Indexing Content.
    Follows Single Responsibility Principle by delegating specific tasks to injected dependencies.
    """

    def __init__(
        self,
        structure_repo: StructureNodeRepository,
        ingestor: Ingestor,
        vector_store: Optional[Any] = None,
        storage_context: Optional[StorageContext] = None,
        should_mock_embedding: bool = False
    ):
        self.structure_repo = structure_repo
        self.ingestor = ingestor
        self.vector_store = vector_store
        self.storage_context = storage_context
        self.should_mock_embedding = should_mock_embedding

    def ingest_book(
        self,
        file_path: str,
        book_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None
    ) -> None:
        """
        Main entry point for ingesting a book.
        """
        if book_id is None:
            book_id = uuid.uuid4()

        print(f"--- Starting Ingestion for Book ID: {book_id} ---")
        print(f"Source: {file_path}")

        # 1. Parse Document
        nodes, atoms, detected_category = self._parse_document(file_path, book_id, category)
        print(f"Parsed {len(nodes)} structure nodes and {len(atoms)} content atoms. Category: {detected_category}")

        # 2. Persist Structure Nodes
        self._persist_structure(nodes)

        # 3. Index Content Atoms
        self._index_content(atoms, nodes)

        # 4. Trigger Async Tasks (if applicable)
        self._trigger_async_tasks()

        print("Ingestion complete.")

    def _parse_document(
        self,
        file_path: str,
        book_id: uuid.UUID,
        category: Optional[str]
    ) -> Tuple[List[StructureNode], List[ContentAtom], str]:
        """
        Delegates parsing to the Ingestor strategy.
        """
        nodes = []
        atoms = []
        detected_category = category

        if str(file_path).endswith(".json"):
            print("Detected JSON input. Loading directly...")
            with open(file_path, "r") as f:
                data = json.load(f)

            if detected_category is None:
                 texts = data.get("texts", [])
                 sample_text = "\n".join([t.get("text", "") for t in texts[:5]])
                 detected_category = detect_book_category(os.path.basename(file_path), sample_text)

            nodes, atoms = self.ingestor._parse_docling_structure(data, book_id, file_path, detected_category)
        else:
            # If category is not provided, the ingestor might detect it internally or default.
            # However, the current Ingestor interface ingest_book takes category.
            # If we want to detect BEFORE ingest, we might need to peek at the file.
            # The HybridIngestor does auto-detection internally if category is None.
            nodes, atoms = self.ingestor.ingest_book(str(file_path), book_id, detected_category)
            # We don't easily get the detected category back from ingest_book in the current signature
            # unless we inspect the atoms' metadata.
            if detected_category is None and atoms:
                 # Infer from first atom
                 if hasattr(atoms[0].meta_data, 'category'):
                     detected_category = atoms[0].meta_data.category

        return nodes, atoms, detected_category

    def _persist_structure(self, nodes: List[StructureNode]) -> None:
        """
        Delegates persistence to the StructureNodeRepository.
        """
        print(f"Using repository: {self.structure_repo.__class__.__name__} for structure nodes...")
        try:
            self.structure_repo.ensure_schema()
            self.structure_repo.insert_structure_nodes(nodes)
        except Exception as e:
            print(f"Error during structure node insertion: {e}")
            raise

    def _index_content(self, atoms: List[ContentAtom], nodes: List[StructureNode]) -> None:
        """
        Converts atoms to LlamaIndex Nodes and persists them.
        """
        if not atoms:
            print("No atoms to index.")
            return

        print("Converting atoms to LlamaIndex Nodes...")
        sequence_map = {str(n.id): n.sequence_index for n in nodes}
        llama_nodes = []

        for atom in atoms:
            # Serialize Pydantic metadata
            meta_dict = atom.meta_data.model_dump(exclude_none=True)

            metadata = {
                "book_id": str(atom.book_id),
                "node_id": str(atom.node_id) if atom.node_id else None,
                "atom_type": atom.atom_type,
                **meta_dict
            }

            if sequence_map and str(atom.node_id) in sequence_map:
                metadata["sequence_index"] = sequence_map[str(atom.node_id)]

            node = TextNode(
                text=atom.content_text,
                metadata=metadata,
                id_=str(atom.id)
            )
            llama_nodes.append(node)

        self._setup_and_build_index(llama_nodes)

    def _setup_and_build_index(self, nodes: List[TextNode]) -> VectorStoreIndex:
        """
        Configures VectorStore and EmbeddingModel, then builds the index.
        """
        # Setup Vector Store
        vector_store = self.vector_store
        if vector_store is None and self.storage_context is None:
            vector_store = PGVectorStore.from_params(
                database=os.getenv("POSTGRES_DB", "rag"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                password=os.getenv("POSTGRES_PASSWORD", "rag"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                user=os.getenv("POSTGRES_USER", "rag"),
                table_name="content_atoms",
                embed_dim=1536
            )

        # Setup Storage Context
        storage_context = self.storage_context
        if storage_context is None:
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Setup Embedding Model
        if self.should_mock_embedding:
            print("Using Mock Embeddings...")
            embed_model = MockEmbedding(embed_dim=1536)
        else:
            print("Using OpenAI Embeddings...")
            embed_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=os.getenv("OPENAI_API_KEY")
            )

        print(f"Created {len(nodes)} nodes. Connecting to Vector Store...")
        index = VectorStoreIndex(
            nodes,
            storage_context=storage_context,
            embed_model=embed_model
        )
        print("Success! Atoms Indexed into Vector Store.")
        return index

    def _trigger_async_tasks(self) -> None:
        """
        Triggers post-ingestion async tasks (e.g. vision enrichment).
        """
        # We detect if we are using the Postgres repo to decide if we should trigger Celery
        # This checks the class name string to avoid importing concrete class if not needed
        repo_name = self.structure_repo.__class__.__name__

        if "Postgres" in repo_name:
            try:
                # Local import to avoid circular dependency
                from app.celery_worker import enrich_images_task
                print("Triggering vision enrichment task...")
                enrich_images_task.delay(batch_size=50)
            except ImportError:
                print("Warning: app.celery_worker not found. Vision enrichment skipped.")
            except Exception as e:
                print(f"Warning: Failed to trigger vision enrichment: {e}")
        else:
            print("Skipping async vision enrichment in non-postgres mode.")
