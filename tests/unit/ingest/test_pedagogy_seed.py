import json

import pytest

from ingest.pedagogy_seed import load_pedagogy_seed


def test_load_pedagogy_seed_json(tmp_path):
    seed = [{"content": "Use short prompts.", "meta_data": {"tone": "friendly"}}]
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(seed), encoding="utf-8")

    entries = load_pedagogy_seed(path)

    assert len(entries) == 1
    assert entries[0]["content"] == "Use short prompts."
    assert entries[0]["meta_data"]["tone"] == "friendly"


def test_load_pedagogy_seed_markdown(tmp_path):
    path = tmp_path / "seed.md"
    path.write_text("Focus on speaking practice.", encoding="utf-8")

    entries = load_pedagogy_seed(path)

    assert len(entries) == 1
    assert "speaking practice" in entries[0]["content"]
    assert entries[0]["meta_data"]["source"] == "seed.md"


def test_load_pedagogy_seed_unsupported(tmp_path):
    path = tmp_path / "seed.csv"
    path.write_text("bad format", encoding="utf-8")

    with pytest.raises(ValueError):
        load_pedagogy_seed(path)
