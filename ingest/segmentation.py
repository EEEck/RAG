from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

from .models import DocBlock, LessonChunk


class SegmentationRules:
    def __init__(
        self,
        unit_heading_pattern: str = r"\bUnit\s+(\d+)",
        lesson_heading_pattern: str = r"\b(Lesson\s+\d+(?:\.\d+)?|Pick-up\s+[A-Z])",
        vocab_heading_pattern: str = r"\b(Vocabulary|Word\s+bank)\b",
    ):
        self.unit_heading_pattern = re.compile(unit_heading_pattern, flags=re.IGNORECASE)
        self.lesson_heading_pattern = re.compile(
            lesson_heading_pattern, flags=re.IGNORECASE
        )
        self.vocab_heading_pattern = re.compile(
            vocab_heading_pattern, flags=re.IGNORECASE
        )


def segment_lessons(
    blocks: Iterable[DocBlock],
    rules: SegmentationRules,
    textbook_id: str,
) -> List[LessonChunk]:
    lessons: List[LessonChunk] = []
    current_unit: Optional[int] = None
    current_code: Optional[str] = None
    current_title: Optional[str] = None
    body_lines: List[str] = []
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    def flush():
        nonlocal body_lines, current_code, current_title, current_unit, page_start, page_end
        if not current_code or page_start is None or page_end is None:
            return
        body = "\n".join(body_lines).strip()
        summary = _build_summary(body)
        lessons.append(
            LessonChunk(
                textbook_id=textbook_id,
                unit=current_unit,
                lesson_code=current_code,
                title=current_title or current_code,
                body=body,
                page_start=page_start,
                page_end=page_end,
                summary=summary,
            )
        )
        body_lines = []
        current_code = None
        current_title = None
        page_start = None
        page_end = None

    for block in blocks:
        text = block.cleaned_text
        if not text:
            continue

        unit_match = rules.unit_heading_pattern.search(text)
        if unit_match:
            try:
                current_unit = int(unit_match.group(1))
            except ValueError:
                pass

        lesson_match = rules.lesson_heading_pattern.search(text)
        if lesson_match:
            flush()
            current_code, current_title = _lesson_code_and_title(text, lesson_match)
            page_start = block.page_no
            page_end = block.page_no
            continue

        if current_code:
            body_lines.append(text)
            page_end = block.page_no

    flush()
    return lessons


def _lesson_code_and_title(
    heading_text: str, match: re.Match[str]
) -> Tuple[str, str]:
    title = heading_text.strip()
    token = match.group(1).strip()
    digits = re.findall(r"\d+(?:\.\d+)?", token)
    if digits:
        code = digits[0]
    else:
        code = token
    return code, title


def _build_summary(body: str, max_chars: int = 600) -> str:
    if not body:
        return ""
    text = " ".join(body.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
