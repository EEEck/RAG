from __future__ import annotations

import re
from typing import Iterable, List, Sequence

from .models import DocBlock, LessonChunk, VocabEntry
from .segmentation import SegmentationRules


def extract_vocab_entries(
    blocks: Iterable[DocBlock],
    rules: SegmentationRules,
    textbook_id: str,
) -> List[VocabEntry]:
    """
    Extract vocab rows starting from the first vocab heading until the next lesson/unit heading.
    """
    entries: List[VocabEntry] = []
    collecting = False
    for block in blocks:
        text = block.cleaned_text
        if not text:
            continue
        if rules.vocab_heading_pattern.search(text):
            collecting = True
            continue
        if collecting and (
            rules.lesson_heading_pattern.search(text)
            or rules.unit_heading_pattern.search(text)
        ):
            break
        if not collecting:
            continue
        entries.extend(_parse_block(block, textbook_id))
    return entries


def _parse_block(block: DocBlock, textbook_id: str) -> List[VocabEntry]:
    rows: List[VocabEntry] = []
    if block.block_type == "table":
        lines = [ln for ln in block.text.splitlines() if ln.strip()]
    else:
        lines = _split_lines(block.text)

    for line in lines:
        parsed = _parse_vocab_line(line)
        if not parsed:
            continue
        rows.append(
            VocabEntry(
                textbook_id=textbook_id,
                term=parsed[0],
                lemma=parsed[1],
                pos=parsed[2],
                definition=parsed[3],
                example=parsed[4],
                page=block.page_no,
                source=line,
            )
        )
    return rows


def _split_lines(text: str) -> List[str]:
    parts = []
    for raw in text.splitlines():
        candidate = raw.strip()
        if candidate:
            parts.append(candidate)
    return parts


def _parse_vocab_line(line: str) -> Sequence[str | None]:
    """
    Heuristics to parse a vocab line into term, lemma, pos, definition, example.
    """
    # Table-style with tabs or semicolons
    for sep in ("\t", ";", "  "):
        if sep in line:
            bits = [b.strip() for b in line.split(sep) if b.strip()]
            if len(bits) >= 2:
                term = bits[0]
                definition = bits[1]
                example = bits[2] if len(bits) > 2 else None
                return (term, term.lower(), None, definition, example)

    # "word - definition"
    dash_split = re.split(r"\s[-–]\s", line, maxsplit=1)
    if len(dash_split) == 2:
        term, definition = dash_split
        return (term.strip(), term.lower(), None, definition.strip(), None)

    # Single token fallback
    return (line.strip(), line.strip().lower(), None, None, None)


def link_vocab_to_lessons(
    vocab: List[VocabEntry],
    lessons: Sequence[LessonChunk],
) -> List[VocabEntry]:
    sorted_lessons = sorted(lessons, key=lambda l: (l.page_start, l.page_end))
    for entry in vocab:
        target = _lesson_for_page(entry.page, sorted_lessons)
        if target:
            entry.unit = target.unit
            entry.lesson_code = target.lesson_code
    return vocab


def _lesson_for_page(page: int, lessons: Sequence[LessonChunk]) -> LessonChunk | None:
    containing = [l for l in lessons if l.page_start <= page <= l.page_end]
    if containing:
        return containing[0]
    prior = [l for l in lessons if l.page_end <= page]
    if prior:
        return prior[-1]
    return None
