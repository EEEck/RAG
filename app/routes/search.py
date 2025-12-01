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
    user_id = None
    profile = None

    # 1. Resolve Profile & User ID
    if req.profile_id:
        profile = profile_service.get_profile(req.profile_id)
        if profile:
            user_id = profile.user_id
        elif req.strict_mode:
            # If strict mode requires profile, and it's not found -> 404
            raise HTTPException(status_code=404, detail="Profile not found.")

    # 2. Determine Book Context
    if req.strict_mode:
        if not req.profile_id:
            raise HTTPException(status_code=400, detail="Profile ID is required in strict mode.")

        # At this point, if profile_id is set, we either have a profile or raised 404 above.
        # But if profile_id was set but profile is None (and not strict mode), we continue.
        # Wait, if strict_mode is True, we raised 404. So profile is guaranteed here.

        if not profile.book_list:
            raise HTTPException(
                status_code=400,
                detail="Strict mode is on but no books are assigned to this profile. Please add books or disable strict mode."
            )

        book_ids = profile.book_list
    else:
        # Normal Mode: Explicit book_id overrides everything else
        if req.book_id:
            book_ids = [req.book_id]

    # 3. Execute Search with Privacy Scope
    response = search_service.search_content(
        query=req.query,
        limit=req.top_lessons + req.top_vocab,
        max_unit=req.max_unit,
        max_sequence_index=req.max_sequence_index,
        book_ids=book_ids,
        user_id=user_id
    )
    return response
