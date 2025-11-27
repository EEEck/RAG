from __future__ import annotations

from ingest.models import LessonChunk


def test_segment_lessons_produces_chunks(toy_lessons):
    assert toy_lessons, "Expected at least one lesson chunk"
    for lesson in toy_lessons:
        assert isinstance(lesson, LessonChunk)
        assert lesson.lesson_code
        assert lesson.page_start <= lesson.page_end
        assert lesson.body.strip()


def test_lessons_have_monotonic_pages(toy_lessons):
    pages = [l.page_start for l in toy_lessons]
    assert pages == sorted(pages), "Lesson page_starts should be non-decreasing"

