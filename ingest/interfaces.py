from typing import Protocol, List, Tuple, Optional, Dict, Any
import uuid
from .models import StructureNode, ContentAtom

class StructureNodeRepository(Protocol):
    """Interface for persisting structure nodes."""

    def ensure_schema(self) -> None:
        """Ensures the necessary tables exist."""
        ...

    def insert_structure_nodes(self, nodes: List[StructureNode]) -> None:
        """Inserts a batch of structure nodes."""
        ...

    def list_books(self, subject: str, level: Optional[int] = None, min_level: Optional[int] = None, max_level: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lists available books filtering by subject and grade level.
        Returns a list of dictionaries with book info.
        """
        ...

class Ingestor(Protocol):
    """Interface for document ingestion strategies."""

    def ingest_book(self, file_path: str, book_id: uuid.UUID, category: Optional[str] = None) -> Tuple[List[StructureNode], List[ContentAtom]]:
        """Ingests a book from a file path."""
        ...

    def _parse_docling_structure(self, data: Dict[str, Any], book_id: uuid.UUID, file_path: str, category: str = "language", book_metadata: Dict[str, Any] = None) -> Tuple[List[StructureNode], List[ContentAtom]]:
        """Parses raw structure data (e.g. from JSON)."""
        ...
