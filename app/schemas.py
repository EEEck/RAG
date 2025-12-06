from __future__ import annotations

from typing import List, Optional, Union, Dict, Any, Literal

from pydantic import BaseModel, Field


class BookResponse(BaseModel):
    id: str
    title: str
    subject: str
    grade_level: int
    metadata: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    query: str
    top_lessons: int = 5
    top_vocab: int = 5
    max_unit: Optional[int] = None
    max_sequence_index: Optional[int] = None
    book_id: Optional[str] = None
    profile_id: Optional[str] = None
    strict_mode: bool = False


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


class TimelineArtifact(BaseModel):
    id: str
    date: str
    type: str
    title: str


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
    book_list: List[str] = []


# Agent Schemas

class AgentMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class QuizPlan(BaseModel):
    """Plan to generate a quiz."""
    tool_name: Literal["generate_quiz"] = "generate_quiz"
    book_id: str = Field(..., description="The ID of the textbook.")
    unit: int = Field(..., description="The unit number.")
    topic: str = Field(..., description="The topic of the quiz.")
    description: str = Field(..., description="A short summary of what will be generated.")


class SearchPlan(BaseModel):
    """Plan to search for content."""
    tool_name: Literal["search_content"] = "search_content"
    query: str = Field(..., description="The search query.")
    book_id: Optional[str] = Field(None, description="Optional book ID to filter by.")
    unit: Optional[int] = Field(None, description="Optional unit to filter by.")
    description: str = Field(..., description="A short summary of what will be searched.")

class Clarification(BaseModel):
    """Request for more information from the user."""
    tool_name: Literal["ask_user"] = "ask_user"
    question: str = Field(..., description="The clarifying question to ask the user.")


# Union type for the agent's output
AgentOutput = Union[QuizPlan, SearchPlan, Clarification]


class AgentChatRequest(BaseModel):
    messages: List[AgentMessage]
    profile_id: Optional[str] = None


class AgentChatResponse(BaseModel):
    status: Literal["incomplete", "ready"]
    message: str
    plan: Optional[Union[QuizPlan, SearchPlan]] = None


class ExecutePlanRequest(BaseModel):
    plan: Union[QuizPlan, SearchPlan]
    profile_id: Optional[str] = None
