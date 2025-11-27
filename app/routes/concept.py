from __future__ import annotations

from fastapi import APIRouter

from ..schemas import (
    ConceptPackRequest,
    ConceptPackResponse,
    GenerateItemsRequest,
    GenerateItemsResponse,
)
from ..services.concept_pack import build_concept_pack
from ..services.generation import generate_items


router = APIRouter(prefix="/concept", tags=["concept"])


@router.post("/pack", response_model=ConceptPackResponse)
def concept_pack(req: ConceptPackRequest) -> ConceptPackResponse:
    return build_concept_pack(req)


@router.post("/generate-items", response_model=GenerateItemsResponse)
def generate_items_route(req: GenerateItemsRequest) -> GenerateItemsResponse:
    return generate_items(req)

