from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService, get_profile_service
from app.schemas import AtomHit

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

# Dependency Injection helper
def get_memory_service():
    return MemoryService()

class SaveArtifactRequest(BaseModel):
    profile_id: str
    content: str
    type: str = "lesson"
    summary: Optional[str] = None
    related_book_ids: List[str] = []
    topic_tags: List[str] = []

class ArtifactResponse(BaseModel):
    id: str
    profile_id: str
    type: str
    created_at: str

@router.post("/", response_model=ArtifactResponse)
def save_artifact(
    request: SaveArtifactRequest,
    service: MemoryService = Depends(get_memory_service),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Save a generated item (lesson, quiz) as a memory artifact.
    """
    # Validate Profile Exists
    if not profile_service.get_profile(request.profile_id):
        raise HTTPException(status_code=404, detail=f"Profile with ID {request.profile_id} not found.")

    try:
        artifact = service.save_artifact(
            profile_id=request.profile_id,
            content=request.content,
            artifact_type=request.type,
            summary=request.summary,
            related_book_ids=request.related_book_ids,
            topic_tags=request.topic_tags
        )
        return ArtifactResponse(
            id=str(artifact.id),
            profile_id=artifact.profile_id,
            type=artifact.type,
            created_at=str(artifact.created_at)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[AtomHit])
def list_artifacts(
    profile_id: Optional[str] = Query(None),
    query: Optional[str] = None,
    limit: int = 5,
    service: MemoryService = Depends(get_memory_service),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Retrieve artifacts for a profile, optionally matching a query (semantic search).
    Returns generic AtomHit objects for consistency with Search API.
    """
    if profile_id:
        if not profile_service.get_profile(profile_id):
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found.")
        try:
            hits = service.search_artifacts(profile_id, query, limit)
            return hits
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Search without profile: return empty list as requested for decoupled handling
        return []
