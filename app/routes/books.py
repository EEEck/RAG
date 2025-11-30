from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from app.schemas import BookResponse
from ingest.infra.postgres import PostgresStructureNodeRepository

router = APIRouter(prefix="/books", tags=["books"])

def get_structure_repo():
    return PostgresStructureNodeRepository()

@router.get("/", response_model=List[BookResponse])
def list_books(
    subject: str = Query(..., description="The mandatory subject of the book (e.g. language, stem, history)"),
    level: Optional[int] = Query(None, description="Exact grade level to filter by"),
    min_level: Optional[int] = Query(None, description="Minimum grade level range"),
    max_level: Optional[int] = Query(None, description="Maximum grade level range"),
    repo: PostgresStructureNodeRepository = Depends(get_structure_repo)
):
    """
    List available textbooks with mandatory subject and level filtering.
    Requires either 'level' OR both 'min_level' and 'max_level' to be provided.
    """

    # Validation: Ensure mandatory level filtering
    has_exact_level = level is not None
    has_range_level = min_level is not None and max_level is not None

    if not (has_exact_level or has_range_level):
        raise HTTPException(
            status_code=400,
            detail="Mandatory filtering required: Provide either 'level' (exact) or both 'min_level' and 'max_level' (range)."
        )

    try:
        books_data = repo.list_books(subject=subject, level=level, min_level=min_level, max_level=max_level)

        response = []
        for b in books_data:
            metadata = b.get("metadata", {})
            response.append(BookResponse(
                id=b["book_id"],
                title=b["title"],
                subject=metadata.get("subject", "unknown"),
                grade_level=int(metadata.get("grade_level", 0)),
                metadata=metadata
            ))

        return response
    except Exception as e:
        print(f"Error listing books: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
