from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import DocBlock, BBox


def load_docling_blocks(json_path: Path | str) -> List[DocBlock]:
    """
    Parse a Docling JSON export into a flat list of DocBlock items.

    Keeps text and table blocks with page numbers, sorted by page then order.
    """
    doc = _read_json(json_path)
    blocks: List[DocBlock] = []

    for idx, text_obj in enumerate(doc.get("texts", [])):
        text_val = (text_obj.get("text") or text_obj.get("orig") or "").strip()
        if not text_val:
            continue
        page = _first_page(text_obj.get("prov", []))
        if page is None:
            continue
        blocks.append(
            DocBlock(
                text=text_val,
                page_no=page,
                block_type=text_obj.get("label", "text"),
                level=text_obj.get("level"),
                bbox=_bbox(text_obj),
                order=idx,
            )
        )

    table_offset = len(blocks) + 1000
    for t_idx, table_obj in enumerate(doc.get("tables", [])):
        table_text = _table_to_lines(table_obj)
        if not table_text:
            continue
        page = _first_page(table_obj.get("prov", []))
        if page is None:
            continue
        blocks.append(
            DocBlock(
                text=table_text,
                page_no=page,
                block_type="table",
                level=None,
                bbox=_bbox(table_obj),
                order=table_offset + t_idx,
            )
        )

    return sorted(blocks, key=lambda b: (b.page_no, b.order))


def _read_json(path: Path | str) -> Dict:
    data = Path(path).read_text(encoding="utf-8")
    return json.loads(data)


def _first_page(prov_list: Iterable[Dict]) -> Optional[int]:
    for item in prov_list:
        page = item.get("page_no")
        if page is not None:
            try:
                return int(page)
            except (TypeError, ValueError):
                return None
    return None


def _bbox(obj: Dict) -> Optional[BBox]:
    prov = obj.get("prov") or []
    if not prov:
        return None
    bbox = prov[0].get("bbox") or {}
    if not bbox:
        return None
    coords = (bbox.get("l"), bbox.get("t"), bbox.get("r"), bbox.get("b"))
    if any(v is None for v in coords):
        return None
    return coords  # type: ignore


def _table_to_lines(table_obj: Dict) -> str:
    cells = table_obj.get("data", {}).get("table_cells", [])
    if not cells:
        return ""
    rows: Dict[int, Dict[int, str]] = {}
    for cell in cells:
        row = cell.get("start_row_offset_idx", 0)
        col = cell.get("start_col_offset_idx", 0)
        rows.setdefault(row, {})
        rows[row][col] = (cell.get("text") or "").strip()

    lines: List[str] = []
    for row_idx in sorted(rows):
        row_cells = rows[row_idx]
        cols = [row_cells.get(c, "") for c in sorted(row_cells)]
        line = "\t".join(col for col in cols if col)
        if line.strip():
            lines.append(line)
    return "\n".join(lines)
