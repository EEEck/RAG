from __future__ import annotations

from fastapi import APIRouter

from ..schemas import SearchRequest, SearchResponse
from ..services.search_service import get_search_service


router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    # Service now returns SearchResponse object directly
    search_service = get_search_service()

    response = search_service.search_lessons_and_vocab(
        query=req.query,
        top_lessons=req.top_lessons,
        top_vocab=req.top_vocab,
        max_unit=req.max_unit,
        max_sequence_index=req.max_sequence_index,
    )
    return response
