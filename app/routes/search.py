from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import SearchRequest, SearchResponse
from ..services.search_service import get_search_service
from ..services.profile_service import get_profile_service


router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    # Service now returns SearchResponse object directly
    search_service = get_search_service()
    profile_service = get_profile_service()

    book_ids = None

    if req.strict_mode:
        # Strict Mode: Use Profile's book_list ONLY
        if not req.profile_id:
            raise HTTPException(status_code=400, detail="Profile ID is required in strict mode.")

        profile = profile_service.get_profile(req.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found.")

        # If profile has no books assigned, raise 400
        if not profile.book_list:
            raise HTTPException(
                status_code=400,
                detail="Strict mode is on but no books are assigned to this profile. Please add books or disable strict mode."
            )

        # Use only the profile's books
        book_ids = profile.book_list

    else:
        # Normal Mode:
        # If strict_mode is False, we rely on the explicit book_id if provided.
        # We ignore profile-based restrictions.
        if req.book_id:
            book_ids = [req.book_id]

    response = search_service.search_content(
        query=req.query,
        limit=req.top_lessons + req.top_vocab,
        max_unit=req.max_unit,
        max_sequence_index=req.max_sequence_index,
        book_ids=book_ids
    )
    return response
