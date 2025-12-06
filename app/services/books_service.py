from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel

from ingest.infra.postgres import get_connection

# Simple Book Model for this service
class BookSummary(BaseModel):
    id: str
    title: str
    subject: Optional[str] = None
    grade_level: Optional[int] = None

class BookService:
    def get_book(self, book_id: str) -> Optional[BookSummary]:
        """
        Retrieves a book's basic info from the DB.
        """
        conn = get_connection(db_type="content")
        try:
            with conn.cursor() as cur:
                # Query root node (level 0) for this book
                cur.execute(
                    "SELECT id, title, meta_data FROM structure_nodes WHERE book_id = %s AND node_level = 0 LIMIT 1",
                    (book_id,)
                )
                row = cur.fetchone()
                if row:
                    # id is UUID, title is text, meta is jsonb
                    # Note: row[0] is the node id, not necessarily the book_id (though they are often same for root)
                    # Actually, for level 0, book_id column is the book ID.
                    # Wait, let's check schema.
                    meta = row[2] or {}
                    return BookSummary(
                        id=book_id,
                        title=row[1],
                        subject=meta.get("subject"),
                        grade_level=meta.get("grade_level")
                    )
                return None
        finally:
            conn.close()

def get_book_service() -> BookService:
    return BookService()
