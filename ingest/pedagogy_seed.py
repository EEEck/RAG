from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from .infra.postgres import PedagogyStrategyRepository


def load_pedagogy_seed(path: Path, max_pages: int = 3) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ValueError("JSON seed must be a list or object.")
        entries = []
        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError("Each pedagogy entry must be an object.")
            entries.append(
                {
                    "id": entry.get("id"),
                    "owner_id": entry.get("owner_id"),
                    "content": entry.get("content", ""),
                    "meta_data": entry.get("meta_data") or {},
                }
            )
        return entries

    if suffix in {".md", ".txt"}:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return [
            {
                "content": content,
                "meta_data": {"source": path.name},
            }
        ]

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("pypdf is required to parse PDF pedagogy files.") from exc

        reader = PdfReader(str(path))
        pages = reader.pages[:max_pages]
        content_parts = [(page.extract_text() or "") for page in pages]
        content = "\n".join(part for part in content_parts if part.strip()).strip()
        if not content:
            return []
        return [
            {
                "content": content,
                "meta_data": {"source": path.name, "pages": len(pages)},
            }
        ]

    raise ValueError(f"Unsupported seed format: {suffix}")


def seed_pedagogy(file_path: str, owner_id: str | None = None, max_pages: int = 3) -> int:
    path = Path(file_path)
    entries = load_pedagogy_seed(path, max_pages=max_pages)
    if owner_id:
        for entry in entries:
            entry.setdefault("owner_id", owner_id)

    repo = PedagogyStrategyRepository()
    repo.ensure_schema()
    return repo.upsert_strategies(entries)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed pedagogy strategies into the content DB.")
    parser.add_argument("--file", required=True, help="Path to a .json, .md, .txt, or .pdf seed file.")
    parser.add_argument("--owner-id", default=None, help="Optional owner_id to assign.")
    parser.add_argument("--max-pages", type=int, default=3, help="Max PDF pages to extract.")
    args = parser.parse_args()

    count = seed_pedagogy(args.file, owner_id=args.owner_id, max_pages=args.max_pages)
    print(f"Seeded {count} pedagogy strategy record(s).")


if __name__ == "__main__":
    main()
