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
        """
        Initializes the IngestionService.

        Args:
            structure_repo (StructureNodeRepository): Repository for storing structure nodes.
            ingestor (Ingestor): The strategy for parsing documents (e.g., HybridIngestor).
            vector_store (Optional[Any]): The vector store instance. Defaults to PGVectorStore if None.
            storage_context (Optional[StorageContext]): LlamaIndex storage context.
            should_mock_embedding (bool): If True, uses MockEmbedding instead of OpenAI.
        """
        self.structure_repo = structure_repo
        self.ingestor = ingestor
        self.vector_store = vector_store
        self.storage_context = storage_context
        self.should_mock_embedding = should_mock_embedding

    def ingest_book(
        self,
        file_path: str,
        book_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> None:
        """
        Main entry point for ingesting a book.

        Args:
            file_path (str): Path to the PDF or JSON file.
            book_id (Optional[uuid.UUID]): The ID to assign to the book. Generated if not provided.
            category (Optional[str]): Explicit book category (e.g., 'STEM', 'History'). Auto-detected if None.
            owner_id (Optional[str]): The ID of the user who owns this content. If provided, content is private.
        """
        if book_id is None:
            book_id = uuid.uuid4()

        print(f"--- Starting Ingestion for Book ID: {book_id} ---")
        print(f"Source: {file_path}")
        if owner_id:
            print(f"Owner ID: {owner_id}")

        # 1. Parse Document
        nodes, atoms, detected_category = self._parse_document(file_path, book_id, category)
        print(f"Parsed {len(nodes)} structure nodes and {len(atoms)} content atoms. Category: {detected_category}")

        # 2. Assign owner_id if present
        if owner_id:
            for node in nodes:
                node.owner_id = owner_id

        # 3. Persist Structure Nodes
        self._persist_structure(nodes)

        # 4. Index Content Atoms
        self._index_content(atoms, nodes, owner_id)

        # 5. Trigger Async Tasks (if applicable)
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
                 # We only get category here for logging/return; metadata extraction is inside ingestor
                 detected_category = detect_book_category(os.path.basename(file_path), sample_text)

            # Note: _parse_docling_structure call might need metadata if not handled inside
            # Ideally Ingestor abstraction handles this.
            # But the Ingestor interface _parse_docling_structure has been updated in HybridIngestor
            # but here we are calling it directly via self.ingestor.
            # If self.ingestor is HybridIngestor, it works. If it's a mock/protocol, we need to check signature.
            # For JSON, we use _parse_docling_structure.

            # Since we updated HybridIngestor._parse_docling_structure to accept book_metadata,
            # we should fetch it here or let it default.
            # But since detect_book_category calls detect_book_metadata under the hood now,
            # we can't easily get the full metadata object unless we change this call too.
            # For JSON path (testing usually), defaults are acceptable.

            nodes, atoms = self.ingestor._parse_docling_structure(data, book_id, file_path, detected_category)
        else:
            # If category is not provided, the ingestor might detect it internally or default.
            # The HybridIngestor does auto-detection internally if category is None.
            nodes, atoms = self.ingestor.ingest_book(str(file_path), book_id, detected_category)

            # Try to retrieve detected category from root node metadata if available
            root_node = next((n for n in nodes if n.node_level == 0), None)
            if root_node and isinstance(root_node.meta_data, dict):
                 detected_category = root_node.meta_data.get("subject", detected_category)

            # Fallback if still None
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

    def _index_content(self, atoms: List[ContentAtom], nodes: List[StructureNode], owner_id: Optional[str] = None) -> None:
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

            # Inject owner_id if present
            if owner_id:
                metadata["owner_id"] = owner_id

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
