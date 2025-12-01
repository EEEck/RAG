from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService, get_profile_service
from app.schemas import AtomHit, TimelineArtifact

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


@router.get("/timeline", response_model=List[TimelineArtifact])
def get_artifact_timeline(
    profile_id: str,
    start_date: str, # ISO Format
    end_date: str, # ISO Format
    type: Optional[str] = None,
    limit: int = 20,
    service: MemoryService = Depends(get_memory_service),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Retrieve a timeline of artifacts for a profile, filtered by date range and type.
    """
    if not profile_service.get_profile(profile_id):
        raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found.")

    try:
        # Parse Dates
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)")

        artifacts = service.get_artifacts_in_range(
            profile_id=profile_id,
            start_date=start_dt,
            end_date=end_dt,
            artifact_type=type
        )

        # Convert to TimelineArtifact
        timeline = []
        for art in artifacts[:limit]:
            timeline.append(TimelineArtifact(
                id=str(art.id),
                date=art.created_at.isoformat() if art.created_at else "",
                type=art.type,
                title=art.summary or f"{art.type.capitalize()} on {art.created_at.strftime('%Y-%m-%d')}"
            ))

        return timeline

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
