from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from ..schemas import TeacherProfile
from ..services.profile_service import get_profile_service, ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.post("", response_model=TeacherProfile)
def create_profile(
    profile: TeacherProfile,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Create a new teacher profile.
    """
    return service.create_profile(profile)

@router.get("", response_model=List[TeacherProfile])
def list_profiles(
    user_id: Optional[str] = None,
    service: ProfileService = Depends(get_profile_service)
):
    """
    List teacher profiles.
    """
    return service.list_profiles(user_id)

@router.get("/{profile_id}", response_model=TeacherProfile)
def get_profile(
    profile_id: str,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Get a specific profile by ID.
    """
    p = service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

@router.put("/{profile_id}", response_model=TeacherProfile)
def update_profile(
    profile_id: str,
    updates: TeacherProfile,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Update a teacher profile.
    """
    p = service.update_profile(profile_id, updates)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p
