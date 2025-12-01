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
    category: str = "language"
    profile_id: Optional[str] = None
    use_memory: bool = False


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


class PedagogyConfig(BaseModel):
    tone: Optional[str] = "neutral"
    style: Optional[str] = "standard"
    focus_areas: List[str] = []
    adaptation_level: Optional[str] = "standard"


class ContentScope(BaseModel):
    banned_topics: List[str] = []
    preferred_sources: List[str] = []


class TeacherProfile(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    grade_level: Optional[str] = None
    pedagogy_config: PedagogyConfig = PedagogyConfig()
    content_scope: ContentScope = ContentScope()


class PedagogyStrategy(BaseModel):
    id: Optional[str] = None
    title: str
    subject: str
    min_grade: int = 0
    max_grade: int = 12
    institution_type: Optional[str] = None
    prompt_injection: Union[Dict[str, Any], str]
    summary_for_search: Optional[str] = None # Not always returned to client, but useful
    # embedding not usually in Pydantic schema for API
