from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.memory_service import MemoryService
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
    service: MemoryService = Depends(get_memory_service)
):
    """
    Save a generated item (lesson, quiz) as a memory artifact.
    """
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
    profile_id: str,
    query: Optional[str] = None,
    limit: int = 5,
    service: MemoryService = Depends(get_memory_service)
):
    """
    Retrieve artifacts for a profile, optionally matching a query (semantic search).
    Returns generic AtomHit objects for consistency with Search API.
    """
    try:
        hits = service.search_artifacts(profile_id, query, limit)
        return hits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
