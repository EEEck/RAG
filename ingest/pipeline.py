import uuid
import os
from typing import Optional, Any
from llama_index.core import StorageContext

from .interfaces import StructureNodeRepository, Ingestor
from .service import IngestionService
from .infra.postgres import PostgresStructureNodeRepository

# Keep index_atoms for backward compatibility if needed by tests,
# but point it to the new service logic if possible, or leave as utility.
# However, for `run_ingestion`, we will rewrite it to use the Service.

def index_atoms(
    atoms,
    sequence_map=None,
    should_mock_embedding=False,
    vector_store=None,
    storage_context=None
):
    """
    Deprecated utility. Use IngestionService._index_content logic instead.
    Kept here because some tests might import it directly.
    """
    # We can instantiate a minimal service to reuse the logic
    # But IngestionService needs repositories.
    # Let's just create a dummy service for this utility function to avoid code duplication
    # if we want to be strict. Or we can just copy the logic back here for the legacy util.
    # Given the user wants "Best Practices", duplication is bad.
    # But `index_atoms` requires `atoms` input, whereas `IngestionService` takes file_path usually.
    # `IngestionService._index_content` is internal.

    # For now, I will reimplement it using a transient Service instance or just standalone
    # if I can't easily mock the repo.
    # Actually, `IngestionService` uses `_index_content` which takes `atoms`.
    # Let's make `_index_content` logic available or just inline it here for now to avoid breaking imports
    # without complex refactoring of tests that rely on this specific function signature.

    # Creating a temporary service to use its method is a bit hacky because of the constructor deps.
    # So I will duplicate the logic here for this legacy/test helper function for now,
    # or better, update the tests to use the Service if possible.

    # Since the plan said "Update ingest/pipeline.py... rewrite run_ingestion", I will focus on that.
    # I will leave index_atoms largely as is (or import from service if I made it static) to avoid breaking `tests/integration/test_pipeline_local.py`.
    # Actually, `test_pipeline_local.py` calls `pipeline.index_atoms`.

    # Strategy: Keep `index_atoms` as a wrapper or standalone for tests.
    # Rewriting `run_ingestion` to use `IngestionService`.

    from llama_index.core.schema import TextNode
    from llama_index.core import VectorStoreIndex
    from llama_index.vector_stores.postgres import PGVectorStore
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core.embeddings import MockEmbedding

    if not atoms:
        return None

    nodes = []
    for atom in atoms:
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
        nodes.append(node)

    if vector_store is None and storage_context is None:
        vector_store = PGVectorStore.from_params(
            database=os.getenv("POSTGRES_DB", "rag"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            password=os.getenv("POSTGRES_PASSWORD", "rag"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER", "rag"),
            table_name="content_atoms",
            embed_dim=1536
        )

    if storage_context is None:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if should_mock_embedding:
        embed_model = MockEmbedding(embed_dim=1536)
    else:
        embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

    return VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model
    )


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
    Wrapper for IngestionService to maintain backward compatibility.
    """

    # Default Dependencies
    if structure_repo is None:
        structure_repo = PostgresStructureNodeRepository()

    if ingestor is None:
        try:
            from .hybrid_ingestor import HybridIngestor
            ingestor = HybridIngestor()
        except ImportError as e:
            print(f"Error importing HybridIngestor: {e}")
            return

    # Instantiate Service
    service = IngestionService(
        structure_repo=structure_repo,
        ingestor=ingestor,
        vector_store=vector_store,
        storage_context=storage_context,
        should_mock_embedding=should_mock_embedding
    )

    # Run
    service.ingest_book(file_path, book_id, category)

if __name__ == "__main__":
    pass
