import uuid
import os
import json
import pytest
from uuid import UUID
import sqlite3
from typing import Any

from ingest.models import ContentAtom, StructureNode
from ingest.schemas import LanguageMetadata
from ingest import db, pipeline
from app.services.search import search_lessons_and_vocab, set_index_override

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.vector_stores import SimpleVectorStore

# Hardcoded Test Data (from original integration_rag.py)
DATA_NODES = [StructureNode(id=UUID('00ffc99b-5c33-4ba6-ab84-b075146cd543'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), parent_id=None, node_level=0, title='Book Root', sequence_index=0, meta_data={}), StructureNode(id=UUID('84c4f19c-a53a-4903-a5e4-b83e369bc163'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), parent_id=UUID('00ffc99b-5c33-4ba6-ab84-b075146cd543'), node_level=1, title="Pick-up A We're from Greenwich", sequence_index=1, meta_data={'page_no': 1, 'bbox': {'l': 586.2127685546875, 't': 3877.1612955729165, 'r': 1995.5745442708333, 'b': 3548.9032389322915, 'coord_origin': 'BOTTOMLEFT'}, 'charspan': [0, 30]}), StructureNode(id=UUID('8f27bee1-60be-46a8-8cc2-ce04806a4242'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), parent_id=UUID('00ffc99b-5c33-4ba6-ab84-b075146cd543'), node_level=1, title='3 Characters', sequence_index=2, meta_data={'page_no': 1, 'bbox': {'l': 441.1914876302083, 't': 644.1292317708335, 'r': 906.8936360677084, 'b': 534.7096354166665, 'coord_origin': 'BOTTOMLEFT'}, 'charspan': [0, 12]}), StructureNode(id=UUID('33466cae-ff92-49f8-8d1b-cc067792f9a9'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), parent_id=UUID('00ffc99b-5c33-4ba6-ab84-b075146cd543'), node_level=1, title='Media skills', sequence_index=3, meta_data={'page_no': 2, 'bbox': {'l': 1830.1277669270833, 't': 712.2581380208335, 'r': 2126.2980143229165, 'b': 658.5807291666665, 'coord_origin': 'BOTTOMLEFT'}, 'charspan': [0, 12]})]

DATA_ATOMS = [ContentAtom(id=UUID('61e2fd8b-11ec-4363-a765-74ff48833d94'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), node_id=UUID('00ffc99b-5c33-4ba6-ab84-b075146cd543'), atom_type='text', content_text='1/1 ?', meta_data=LanguageMetadata(book_id='4f10954b-c1cc-478a-952f-0bd2b954c672', unit_number=0, page_number=1, section_title=None, content_type='text', category='language', cefr_level=None, vocab_word=None, word_class=None, grammar_topic=None, speaker=None), embedding=None), ContentAtom(id=UUID('6334d878-e9de-4015-972d-310664fa8943'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), node_id=UUID('84c4f19c-a53a-4903-a5e4-b83e369bc163'), atom_type='text', content_text="Here's your ball,", meta_data=LanguageMetadata(book_id='4f10954b-c1cc-478a-952f-0bd2b954c672', unit_number=0, page_number=1, section_title=None, content_type='text', category='language', cefr_level=None, vocab_word=None, word_class=None, grammar_topic=None, speaker=None), embedding=None), ContentAtom(id=UUID('ac8ea025-13f4-4b6e-8594-e8bd0d5535fb'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), node_id=UUID('8f27bee1-60be-46a8-8cc2-ce04806a4242'), atom_type='text', content_text="We're from Greenwich.", meta_data=LanguageMetadata(book_id='4f10954b-c1cc-478a-952f-0bd2b954c672', unit_number=0, page_number=1, section_title=None, content_type='text', category='language', cefr_level=None, vocab_word=None, word_class=None, grammar_topic=None, speaker=None), embedding=None), ContentAtom(id=UUID('005391b3-4931-4f74-9c33-2c9538342f3c'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), node_id=UUID('8f27bee1-60be-46a8-8cc2-ce04806a4242'), atom_type='text', content_text="We're from Greenwich. Where are you from?", meta_data=LanguageMetadata(book_id='4f10954b-c1cc-478a-952f-0bd2b954c672', unit_number=0, page_number=2, section_title=None, content_type='text', category='language', cefr_level=None, vocab_word=None, word_class=None, grammar_topic=None, speaker=None), embedding=None), ContentAtom(id=UUID('fac11a19-f166-43dc-8060-78b089871914'), book_id=UUID('4f10954b-c1cc-478a-952f-0bd2b954c672'), node_id=UUID('8f27bee1-60be-46a8-8cc2-ce04806a4242'), atom_type='text', content_text='Tony: Greenwich? Me too.', meta_data=LanguageMetadata(book_id='4f10954b-c1cc-478a-952f-0bd2b954c672', unit_number=0, page_number=2, section_title=None, content_type='text', category='language', cefr_level=None, vocab_word=None, word_class=None, grammar_topic=None, speaker=None), embedding=None)]

# Mock Entry to Add
MOCK_NODE_ID = uuid.uuid4()
MOCK_ATOM_ID = uuid.uuid4()
MOCK_BOOK_ID = UUID('4f10954b-c1cc-478a-952f-0bd2b954c672')

MOCK_NODE = StructureNode(
    id=MOCK_NODE_ID,
    book_id=MOCK_BOOK_ID,
    parent_id=UUID('00ffc99b-5c33-4ba6-ab84-b075146cd543'),
    node_level=1,
    title='Mock Section',
    sequence_index=2,
    meta_data={'page_no': 99}
)

MOCK_ATOM = ContentAtom(
    id=MOCK_ATOM_ID,
    book_id=MOCK_BOOK_ID,
    node_id=MOCK_NODE_ID,
    atom_type='text',
    content_text='This is a mock integration test entry for RAG verification.',
    meta_data=LanguageMetadata(
        book_id=str(MOCK_BOOK_ID),
        unit_number=99,
        page_number=99,
        content_type='text',
        category='language'
    )
)

@pytest.fixture
def sqlite_db_path(tmp_path):
    """Fixture to provide a temporary SQLite DB path."""
    return str(tmp_path / "test_rag.db")

@pytest.fixture
def storage_context():
    """Fixture to provide a full StorageContext (DocStore + VectorStore)."""
    return StorageContext.from_defaults(vector_store=SimpleVectorStore())

def test_pipeline_local_integration(sqlite_db_path, storage_context):
    """
    Integration test that:
    1. Sets up a local SQLite DB.
    2. Sets up a local StorageContext (holding both vectors and text).
    3. Ingests structure nodes and content atoms (including a new mock one).
    4. Performs a RAG search using the Search Service.
    5. Verifies the results.
    """

    # 1. Prepare Data
    nodes = DATA_NODES + [MOCK_NODE]
    atoms = DATA_ATOMS + [MOCK_ATOM]

    print(f"\nUsing SQLite DB at: {sqlite_db_path}")

    # 2. Persist Structure Nodes (SQLite)
    conn = db.get_db_connection(mode="sqlite", db_path=sqlite_db_path)
    try:
        db.ensure_schema(conn)
        db.insert_structure_nodes(conn, nodes)

        # Verify Insertion
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM structure_nodes")
        count = cur.fetchone()[0]
        assert count == len(nodes), f"Expected {len(nodes)} nodes, found {count}"

    finally:
        conn.close()

    # 3. Index Atoms (using the persistent StorageContext)
    # Create sequence map
    sequence_map = {str(n.id): n.sequence_index for n in nodes}

    # Run Indexing
    # This now returns the live Index object
    index = pipeline.index_atoms(
        atoms,
        sequence_map=sequence_map,
        should_mock_embedding=False, # Use Real OpenAI Embeddings
        storage_context=storage_context
    )

    # 4. Setup Search Service Override
    # Pass the LIVE index object to the search service
    set_index_override(index)

    # 5. Perform RAG Search
    # Query for the mock entry
    query = "mock integration test"
    response = search_lessons_and_vocab(query, top_lessons=5)

    print("\n--- Search Results ---")
    for atom in response.atoms:
        print(f"[{atom.score:.4f}] {atom.content}")

    # 6. Assertions
    found_mock = False
    for atom in response.atoms:
        if "mock integration test entry" in atom.content:
            found_mock = True
            break

    assert found_mock, "The mock entry was not found in the RAG search results."

    # Verify original data also findable
    query_orig = "Greenwich"
    response_orig = search_lessons_and_vocab(query_orig, top_lessons=5)

    print("\n--- Original Data Search Results ---")
    for atom in response_orig.atoms:
        print(f"[{atom.score:.4f}] {atom.content}")

    found_orig = any("Greenwich" in a.content for a in response_orig.atoms)
    assert found_orig, "Original data regarding Greenwich was not found."

if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    sys.exit(pytest.main(["-s", __file__]))
