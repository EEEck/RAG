from __future__ import annotations

from typing import List, Optional, Union, Dict, Any

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_lessons: int = 5
    top_vocab: int = 5
    max_unit: Optional[int] = None
    max_sequence_index: Optional[int] = None


class AtomHit(BaseModel):
    id: str  # changed to str to accommodate UUID or hash
    content: str
    metadata: Dict[str, Any]
    score: float


class LessonHit(BaseModel):
    id: int
    lesson_code: str
    title: str
    unit: Optional[int]
    score: float
    content: Optional[str] = None  # Added content field


class VocabHit(BaseModel):
    id: int
    term: str
    lesson_code: Optional[str]
    unit: Optional[int]
    score: float
    content: Optional[str] = None  # Added content field


class SearchResponse(BaseModel):
    lessons: List[LessonHit]
    vocab: List[VocabHit]
    atoms: Optional[List[AtomHit]] = None # Generic results


class ConceptPack(BaseModel):
    vocab: List[str]
    grammar_rules: List[str] = []
    themes: List[str] = []


class ConceptPackRequest(BaseModel):
    textbook_id: str
    lesson_code: str
    request_text: Optional[str] = None
    k_lessons: int = 8
    k_vocab: int = 50


class ConceptPackResponse(BaseModel):
    anchor_lesson_id: int
    allowed_scope_count: int
    concept_pack: ConceptPack


class GenerateItemsRequest(BaseModel):
    textbook_id: str
    lesson_code: str
    concept_pack: ConceptPack
    count: int = 10
    item_types: List[str] = ["mcq", "cloze"]
    difficulty: str = "B1"
    context_text: Optional[str] = None # Added for RAG context


class GeneratedItem(BaseModel):
    stem: str
    options: Optional[List[str]] = None
    answer: Optional[Union[int, str]] = None
    concept_tags: List[str] = []
    uses_image: bool = False


class ScopeReport(BaseModel):
    violations: int
    notes: List[str] = []


class GenerateItemsResponse(BaseModel):
    items: List[GeneratedItem]
    scope_report: ScopeReport
