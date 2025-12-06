import pytest
import json
from ingest.docling_parser import load_docling_blocks
from ingest.models import DocBlock

def test_load_docling_blocks(tmp_path):
    # Create dummy json
    data = {
        "texts": [
            {"text": "Hello", "prov": [{"page_no": 1}], "level": 1, "label": "header"},
            {"text": "World", "prov": [{"page_no": 1}], "level": 2}
        ],
        "tables": []
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    blocks = load_docling_blocks(p)
    assert len(blocks) == 2
    assert blocks[0].text == "Hello"
    assert blocks[0].page_no == 1
    assert blocks[0].block_type == "header"

def test_load_docling_tables(tmp_path):
    data = {
        "texts": [],
        "tables": [
            {
                "data": {
                    "table_cells": [
                        {"start_row_offset_idx": 0, "start_col_offset_idx": 0, "text": "A"},
                        {"start_row_offset_idx": 0, "start_col_offset_idx": 1, "text": "B"}
                    ]
                },
                "prov": [{"page_no": 2}]
            }
        ]
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    blocks = load_docling_blocks(p)
    assert len(blocks) == 1
    assert blocks[0].block_type == "table"
    assert "A\tB" in blocks[0].text
