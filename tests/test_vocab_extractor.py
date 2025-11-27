from __future__ import annotations

from ingest.models import VocabEntry


def test_vocab_extraction_basic(toy_vocab):
    assert toy_vocab, "Expected vocab entries from end-of-book section"
    for entry in toy_vocab:
        assert isinstance(entry, VocabEntry)
        assert entry.term.strip()
        assert entry.textbook_id == "toy-green-line-1"
        assert entry.page > 0


def test_vocab_linked_to_lessons_where_possible(toy_vocab):
    linked = [v for v in toy_vocab if v.lesson_code is not None]
    # Not all entries must be linked, but we expect some linkage
    assert len(linked) >= 1

