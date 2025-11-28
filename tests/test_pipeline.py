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

class TestIngestionPipeline(unittest.TestCase):

    @patch("ingest.db.psycopg.connect")
    @patch("ingest.hybrid_ingestor.HybridIngestor.ingest_book")
    def test_run_ingestion_flow(self, mock_ingest_book, mock_connect):
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

        # Run Pipeline
        run_ingestion("dummy.pdf", book_id=book_id, should_mock_embedding=True)

        # Assertions

        # 1. Check DB Connection
        mock_connect.assert_called_once()

        # 2. Check Partition Creation
        # create_partition calls "SELECT create_book_partition(%s)"
        mock_cursor.execute.assert_any_call("SELECT create_book_partition(%s)", (book_id,))

        # 3. Check Insertions
        # We expect executemany to be called twice (nodes and atoms)
        self.assertEqual(mock_cursor.executemany.call_count, 2)

        # Verify Node Insert
        args_nodes = mock_cursor.executemany.call_args_list[0]
        sql_nodes = args_nodes[0][0]
        self.assertIn("INSERT INTO structure_nodes", sql_nodes)

        # Verify Atom Insert
        args_atoms = mock_cursor.executemany.call_args_list[1]
        sql_atoms = args_atoms[0][0]
        self.assertIn("INSERT INTO content_atoms", sql_atoms)

        # 4. Verify Embeddings Mocked
        # The passed atom object should now have an embedding
        self.assertIsNotNone(mock_atoms[0].embedding)
        self.assertEqual(len(mock_atoms[0].embedding), 1536)

    @patch("ingest.db.psycopg.connect")
    def test_json_loading(self, mock_connect):
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
