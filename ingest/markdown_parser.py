from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import ContentAtom, StructureNode
from .schemas import HistoryMetadata, LanguageMetadata, STEMMetadata

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_UNIT_RE = re.compile(r"\bUnit\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class MarkdownSection:
    title: str
    body: str
    heading_level: int
    order: int
    unit_number: Optional[int] = None


def parse_markdown_sections(text: str) -> List[MarkdownSection]:
    sections: List[MarkdownSection] = []
    current_title: Optional[str] = None
    current_level = 1
    current_lines: List[str] = []
    order = 0

    def flush_section() -> None:
        nonlocal order, current_title, current_level, current_lines
        if current_title is None and not current_lines:
            return
        title = current_title or "Untitled Section"
        body = "\n".join(current_lines).strip()
        order += 1
        unit_number = _extract_unit_number(title)
        sections.append(
            MarkdownSection(
                title=title,
                body=body,
                heading_level=current_level,
                order=order,
                unit_number=unit_number,
            )
        )
        current_title = None
        current_level = 1
        current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("<!--") and "image" in stripped:
            continue
        if stripped.startswith("![") and "](" in stripped:
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            flush_section()
            current_level = len(heading_match.group(1))
            current_title = heading_match.group(2).strip()
            continue

        current_lines.append(line)

    flush_section()
    return sections


def build_markdown_nodes_and_atoms(
    sections: List[MarkdownSection],
    book_id: uuid.UUID,
    category: str,
    book_metadata: Optional[Dict[str, object]] = None,
) -> Tuple[List[StructureNode], List[ContentAtom]]:
    nodes: List[StructureNode] = []
    atoms: List[ContentAtom] = []

    root_id = uuid.uuid4()
    root_meta = dict(book_metadata or {})
    root_meta.setdefault("subject", category)
    root_meta.setdefault("source", "markdown")

    nodes.append(
        StructureNode(
            id=root_id,
            book_id=book_id,
            parent_id=None,
            node_level=0,
            title="Book Root",
            sequence_index=0,
            meta_data=root_meta,
        )
    )

    current_parents: Dict[int, uuid.UUID] = {0: root_id}

    for section in sections:
        node_level = max(1, section.heading_level)
        parent_level = node_level - 1
        while parent_level >= 0 and parent_level not in current_parents:
            parent_level -= 1
        parent_id = current_parents.get(parent_level, root_id)

        node_id = uuid.uuid4()
        node_meta: Dict[str, object] = {"source": "markdown"}
        if section.unit_number is not None:
            node_meta["unit"] = section.unit_number

        nodes.append(
            StructureNode(
                id=node_id,
                book_id=book_id,
                parent_id=parent_id,
                node_level=node_level,
                title=section.title[:200],
                sequence_index=section.order,
                meta_data=node_meta,
            )
        )
        current_parents[node_level] = node_id

        if section.body:
            meta = _metadata_for_category(
                category=category,
                book_id=str(book_id),
                unit_number=section.unit_number,
                section_title=section.title,
            )
            atoms.append(
                ContentAtom(
                    id=uuid.uuid4(),
                    book_id=book_id,
                    node_id=node_id,
                    atom_type="text",
                    content_text=section.body,
                    meta_data=meta,
                )
            )

    return nodes, atoms


def _extract_unit_number(title: str) -> Optional[int]:
    match = _UNIT_RE.search(title)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _metadata_for_category(
    category: str,
    book_id: str,
    unit_number: Optional[int],
    section_title: Optional[str],
):
    if category == "stem":
        return STEMMetadata(
            book_id=book_id,
            unit_number=unit_number,
            page_number=None,
            section_title=section_title,
            content_type="text",
        )
    if category == "history":
        return HistoryMetadata(
            book_id=book_id,
            unit_number=unit_number,
            page_number=None,
            section_title=section_title,
            content_type="text",
        )
    return LanguageMetadata(
        book_id=book_id,
        unit_number=unit_number,
        page_number=None,
        section_title=section_title,
        content_type="text",
    )


def load_markdown_sections(path: Path | str) -> List[MarkdownSection]:
    text = Path(path).read_text(encoding="utf-8")
    return parse_markdown_sections(text)
