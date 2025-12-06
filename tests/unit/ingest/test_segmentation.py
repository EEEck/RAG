import pytest
from ingest.segmentation import segment_lessons, SegmentationRules
from ingest.models import DocBlock

def test_segment_lessons_basic():
    rules = SegmentationRules()
    textbook_id = "test-book"

    blocks = [
        DocBlock(text="Unit 1", page_no=1, block_type="header"),
        DocBlock(text="Lesson 1.1 Hello World", page_no=1, block_type="header"),
        DocBlock(text="This is content.", page_no=1),
        DocBlock(text="More content.", page_no=2),
        DocBlock(text="Lesson 1.2 Goodbye", page_no=2, block_type="header"),
        DocBlock(text="Bye content.", page_no=2),
    ]

    chunks = segment_lessons(blocks, rules, textbook_id)

    assert len(chunks) == 2

    c1 = chunks[0]
    assert c1.unit == 1
    assert c1.lesson_code == "1.1"
    assert c1.body.strip() == "This is content.\nMore content."
    assert c1.page_start == 1
    assert c1.page_end == 2

    c2 = chunks[1]
    assert c2.unit == 1 # Persists from previous
    assert c2.lesson_code == "1.2"
    assert c2.body.strip() == "Bye content."

def test_segment_no_lessons():
    rules = SegmentationRules()
    blocks = [DocBlock(text="Just random text", page_no=1)]
    chunks = segment_lessons(blocks, rules, "id")
    assert len(chunks) == 0

def test_segment_custom_pattern():
    rules = SegmentationRules(lesson_heading_pattern=r"(Chapter \d+)")
    blocks = [
        DocBlock(text="Chapter 1 The Beginning", page_no=1),
        DocBlock(text="Content", page_no=1)
    ]
    chunks = segment_lessons(blocks, rules, "id")
    assert len(chunks) == 1
    assert chunks[0].lesson_code == "1"
