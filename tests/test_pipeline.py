import unittest
from unittest.mock import MagicMock, patch
import uuid
import sys
import os
import json

# Add root to path
sys.path.append(os.path.abspath("."))

from ingest.pipeline import run_ingestion
from ingest import db
from ingest.models import StructureNode, ContentAtom
from llama_index.core.schema import TextNode

class TestIngestionPipeline(unittest.TestCase):

    @patch("ingest.pipeline.PGVectorStore")
    @patch("ingest.pipeline.VectorStoreIndex")
    @patch("ingest.db.psycopg.connect")
    @patch("ingest.hybrid_ingestor.HybridIngestor.ingest_book")
    def test_run_ingestion_flow(self, mock_ingest_book, mock_connect, mock_vector_index, mock_pg_store):
        # Setup Mock DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Setup Mock Ingestion Result
        book_id = uuid.uuid4()
        node_id = uuid.uuid4()

        mock_nodes = [
            StructureNode(id=node_id, book_id=book_id, parent_id=None, node_level=0, title="Test", sequence_index=0, meta_data={})
        ]
        mock_atoms = [
            ContentAtom(id=uuid.uuid4(), book_id=book_id, node_id=node_id, atom_type="text", content_text="Hello World", meta_data={})
        ]

        mock_ingest_book.return_value = (mock_nodes, mock_atoms)

        # Mock VectorStore and Index
        mock_store_instance = MagicMock()
        mock_pg_store.from_params.return_value = mock_store_instance

        # Run Pipeline
        run_ingestion("dummy.pdf", book_id=book_id, should_mock_embedding=True)

        # Assertions

        # 1. Check DB Connection (Structure Nodes)
        mock_connect.assert_called()

        # 2. Check Insertions
        # We expect executemany to be called ONCE (structure nodes only)
        # Note: ensure_schema calls execute, but not executemany
        self.assertEqual(mock_cursor.executemany.call_count, 1)

        # Verify Node Insert
        args_nodes = mock_cursor.executemany.call_args_list[0]
        sql_nodes = args_nodes[0][0]
        self.assertIn("INSERT INTO structure_nodes", sql_nodes)

        # 3. Check LlamaIndex Usage
        mock_pg_store.from_params.assert_called_once()
        mock_vector_index.assert_called_once()

        # Check that nodes passed to VectorStoreIndex correspond to atoms
        args_index, _ = mock_vector_index.call_args
        passed_nodes = args_index[0] # first arg is nodes list
        self.assertEqual(len(passed_nodes), 1)
        self.assertIsInstance(passed_nodes[0], TextNode)
        self.assertEqual(passed_nodes[0].text, "Hello World")
        self.assertEqual(passed_nodes[0].metadata["book_id"], str(book_id))

    @patch("ingest.pipeline.PGVectorStore")
    @patch("ingest.pipeline.VectorStoreIndex")
    @patch("ingest.db.psycopg.connect")
    def test_json_loading(self, mock_connect, mock_vector_index, mock_pg_store):
        # Test the JSON path specifically
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # We need a real temporary JSON file
        data = {
            "texts": [
                {"text": "Title", "label": "title", "level": 1},
                {"text": "Paragraph", "label": "text"}
            ]
        }
        with open("temp_test.json", "w") as f:
            json.dump(data, f)

        try:
            run_ingestion("temp_test.json", should_mock_embedding=True)
            # If no exception, it passed the loading phase
        finally:
            if os.path.exists("temp_test.json"):
                os.remove("temp_test.json")

if __name__ == "__main__":
    unittest.main()
