from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock docling if not present to allow collection of tests relying on it
try:
    import docling
except ImportError:
    sys.modules["docling"] = MagicMock()
    sys.modules["docling.document_converter"] = MagicMock()

from pathlib import Path
from typing import List

import pytest

from ingest.docling_parser import load_docling_blocks
from ingest.segmentation import SegmentationRules, segment_lessons
from ingest.vocab_extractor import extract_vocab_entries, link_vocab_to_lessons


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


@pytest.fixture(scope="session")
def toy_doc_path() -> Path:
    path = DATA_DIR / "toy_green_line_1_docling.json"
    if not path.exists():
        pytest.skip("toy Docling JSON not available")
    return path


@pytest.fixture(scope="session")
def toy_blocks(toy_doc_path: Path):
    return load_docling_blocks(toy_doc_path)


@pytest.fixture(scope="session")
def seg_rules() -> SegmentationRules:
    return SegmentationRules()


@pytest.fixture(scope="session")
def toy_lessons(toy_blocks, seg_rules) -> List:
    return segment_lessons(toy_blocks, seg_rules, textbook_id="toy-green-line-1")


@pytest.fixture(scope="session")
def toy_vocab(toy_blocks, seg_rules, toy_lessons) -> List:
    vocab = extract_vocab_entries(toy_blocks, seg_rules, textbook_id="toy-green-line-1")
    return link_vocab_to_lessons(vocab, toy_lessons)
