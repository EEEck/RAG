import uuid
import json
import pytest
from unittest.mock import MagicMock
from ingest.service import IngestionService
from ingest.models import StructureNode, ContentAtom
from ingest.interfaces import Ingestor
from ingest.schemas import LanguageMetadata
from tests.utils.sqlite_test_db import SQLiteTestDB

class MockIngestor(Ingestor):
    def ingest_book(self, file_path, book_id, category=None):
        # Create a simple structure
        root = StructureNode(
            id=uuid.uuid4(),
            book_id=book_id,
            parent_id=None,
            node_level=0,
            title="User Book",
            sequence_index=0,
            meta_data={"subject": "ESL"},
            owner_id=None # Default
        )
        atom = ContentAtom(
            id=uuid.uuid4(),
            book_id=book_id,
            node_id=root.id,
            atom_type="text",
            content_text="This is a private manuscript.",
            meta_data=LanguageMetadata(
                category="language",
                content_type="text",
                cefr_level="A1"
            )
        )
        return [root], [atom]

    def _parse_docling_structure(self, data, book_id, file_path, category=None):
        return [], []

@pytest.fixture
def sqlite_db():
    db = SQLiteTestDB(":memory:")
    db.ensure_schema()
    return db

def test_ingest_user_content_propagates_owner_id(sqlite_db):
    """
    Verifies that when owner_id is passed to IngestionService,
    it is propagated to StructureNodes (DB) and ContentAtoms (Vector Store).
    """
    # 1. Setup Dependencies
    mock_ingestor = MockIngestor()
    mock_vector_store = MagicMock()
    mock_vector_store.add = MagicMock() # LlamaIndex method

    # We need to mock StorageContext to return our mock_vector_store
    mock_storage_context = MagicMock()
    mock_storage_context.vector_store = mock_vector_store

    service = IngestionService(
        structure_repo=sqlite_db, # Use our updated SQLite DB
        ingestor=mock_ingestor,
        storage_context=mock_storage_context,
        should_mock_embedding=True
    )

    # 2. Execute Ingestion with owner_id
    user_id = "teacher_123"
    book_id = uuid.uuid4()
    service.ingest_book(
        file_path="dummy.pdf",
        book_id=book_id,
        category="ESL",
        owner_id=user_id
    )

    # 3. Verify Structure Nodes in SQLite
    conn = sqlite_db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT owner_id FROM structure_nodes WHERE book_id = ?", (str(book_id),))
        row = cur.fetchone()
        assert row is not None
        assert row["owner_id"] == user_id

    # 4. Verify Content Atoms in Vector Store
    # Check mock_vector_store.add parameters
    calls = mock_vector_store.add.call_args_list
    assert len(calls) > 0

    # Get the nodes passed to the first call
    added_nodes = calls[0][0][0] # args[0] is the list of nodes
    assert len(added_nodes) == 1
    node = added_nodes[0]

    # Check metadata
    print(f"Node Metadata: {node.metadata}")
    assert node.metadata["owner_id"] == user_id
    assert node.metadata["book_id"] == str(book_id)
