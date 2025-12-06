import pytest
import uuid
from unittest.mock import MagicMock, patch
from ingest.service import IngestionService
from ingest.models import StructureNode, ContentAtom
from ingest.interfaces import StructureNodeRepository, Ingestor
from ingest.schemas import LanguageMetadata

@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=StructureNodeRepository)
    return repo

@pytest.fixture
def mock_ingestor():
    ingestor = MagicMock(spec=Ingestor)
    return ingestor

@pytest.fixture
def service(mock_repo, mock_ingestor):
    # We mock vector_store and storage_context too to avoid LlamaIndex overhead
    return IngestionService(
        structure_repo=mock_repo,
        ingestor=mock_ingestor,
        vector_store=MagicMock(),
        storage_context=MagicMock(),
        should_mock_embedding=True
    )

def test_ingest_book_flow(service, mock_repo, mock_ingestor):
    # Setup mocks
    book_id = uuid.uuid4()
    node = StructureNode(
        id=uuid.uuid4(),
        book_id=book_id,
        parent_id=None,
        node_level=0,
        title="Root",
        sequence_index=0,
        meta_data={}
    )
    nodes = [node]

    atom = ContentAtom(
        id=uuid.uuid4(),
        book_id=book_id,
        node_id=nodes[0].id,
        atom_type="text",
        content_text="Hello",
        meta_data=LanguageMetadata(book_id=str(book_id), unit_number=1, page_number=1, content_type="text", category="language"),
        embedding=None
    )
    atoms = [atom]

    mock_ingestor.ingest_book.return_value = (nodes, atoms)

    with patch("ingest.service.VectorStoreIndex") as mock_index_cls:
        # Run
        service.ingest_book("test.pdf", book_id=book_id)

        # Verify Ingestor called
        mock_ingestor.ingest_book.assert_called_with("test.pdf", book_id, None)

        # Verify Repo called
        mock_repo.ensure_schema.assert_called_once()
        mock_repo.insert_structure_nodes.assert_called_once_with(nodes)

        # Verify Index created
        mock_index_cls.assert_called_once()

def test_ingest_book_with_owner(service, mock_repo, mock_ingestor):
    # Setup mocks
    book_id = uuid.uuid4()
    node = StructureNode(
        id=uuid.uuid4(),
        book_id=book_id,
        parent_id=None,
        node_level=0,
        title="Root",
        sequence_index=0,
        meta_data={}
    )
    nodes = [node]

    atom = ContentAtom(
        id=uuid.uuid4(),
        book_id=book_id,
        node_id=nodes[0].id,
        atom_type="text",
        content_text="Hello",
        meta_data=LanguageMetadata(book_id=str(book_id), unit_number=1, page_number=1, content_type="text", category="language"),
        embedding=None
    )
    atoms = [atom]

    mock_ingestor.ingest_book.return_value = (nodes, atoms)

    with patch("ingest.service.VectorStoreIndex"):
        service.ingest_book("test.pdf", book_id=book_id, owner_id="teacher_1")

    # Verify owner_id injected
    assert node.owner_id == "teacher_1"

    # Verify Repo called with modified nodes
    mock_repo.insert_structure_nodes.assert_called_once_with(nodes)
