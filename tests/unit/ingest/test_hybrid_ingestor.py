import pytest
from unittest.mock import MagicMock, patch
import uuid

from ingest.hybrid_ingestor import HybridIngestor
from ingest.models import DocBlock

def test_hybrid_ingestor_init():
    ingestor = HybridIngestor()
    assert ingestor is not None
    assert ingestor.docling is not None

def test_parse_docling_structure_json():
    ingestor = HybridIngestor()

    # Mock data structure matching Docling export
    data = {
        "texts": [
            {"text": "Title", "label": "title", "level": 1, "prov": [{"page_no": 1}]},
            {"text": "Paragraph", "label": "text", "level": 2, "prov": [{"page_no": 1}]}
        ],
        "tables": [],
        "pictures": []
    }

    nodes, atoms = ingestor._parse_docling_structure(data, uuid.uuid4(), "file.json", "language")

    assert len(nodes) == 2 # Root + Title
    assert len(atoms) == 1 # Paragraph
    assert nodes[1].title == "Title"
    assert atoms[0].content_text == "Paragraph"

def test_needs_fallback():
    ingestor = HybridIngestor()

    # No tables -> False
    assert ingestor._needs_fallback({"tables": []}) is False

    # Tables with data -> False
    data_good = {"tables": [{"data": "some"}]}
    assert ingestor._needs_fallback(data_good) is False

    # Empty tables -> True (if > 20%)
    data_bad = {"tables": [{"data": None}]}
    assert ingestor._needs_fallback(data_bad) is True

def test_ingest_with_llama():
    ingestor = HybridIngestor()
    ingestor.llama = MagicMock()
    mock_doc = MagicMock()
    mock_doc.text = "Content"
    ingestor.llama.load_data.return_value = [mock_doc]

    nodes, atoms = ingestor.ingest_with_llama("test.pdf", uuid.uuid4())
    assert len(nodes) == 2
    assert len(atoms) == 1
