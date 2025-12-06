import pytest
from ingest.vocab_extractor import extract_vocab_entries, link_vocab_to_lessons
from ingest.segmentation import SegmentationRules
from ingest.models import DocBlock, LessonChunk, VocabEntry

def test_extract_vocab_entries():
    rules = SegmentationRules()
    blocks = [
        DocBlock(text="Unit 1", page_no=1),
        DocBlock(text="Vocabulary", page_no=1, block_type="header"),
        DocBlock(text="apple - a fruit", page_no=1),
        DocBlock(text="banana; a long yellow fruit", page_no=1),
        DocBlock(text="Lesson 2", page_no=2)
    ]

    entries = extract_vocab_entries(blocks, rules, "book1")
    assert len(entries) == 2
    assert entries[0].term == "apple"
    assert entries[0].definition == "a fruit"
    assert entries[1].term == "banana"
    assert entries[1].definition == "a long yellow fruit"

def test_link_vocab_to_lessons():
    vocab = [VocabEntry(textbook_id="b1", term="apple", page=2)]
    lessons = [
        LessonChunk(textbook_id="b1", unit=1, lesson_code="1.1", title="T", body="B", page_start=1, page_end=3)
    ]

    linked = link_vocab_to_lessons(vocab, lessons)
    assert linked[0].unit == 1
    assert linked[0].lesson_code == "1.1"
