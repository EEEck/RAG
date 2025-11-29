from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Level 1: The Base Contract (All Books) ---
class BaseMetadata(BaseModel):
    book_id: Optional[str] = None # Optional during extraction, required for DB
    unit_number: Optional[int] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    content_type: Literal["text", "image", "exercise", "table", "vocab", "image_desc", "grammar", "equation"]

# --- Level 2: Domain-Specific Schemas ---

class LanguageMetadata(BaseMetadata):
    """Schema for ESL / Language Textbooks"""
    category: Literal["language"] = "language"
    cefr_level: Optional[str] = Field(None, description="e.g. A1, B2")
    vocab_word: Optional[str] = Field(None, description="Target word if type=vocab")
    word_class: Optional[str] = Field(None, description="noun, verb, adjective")
    grammar_topic: Optional[str] = Field(None, description="e.g. past_tense")
    speaker: Optional[str] = Field(None, description="For dialogues")

class STEMMetadata(BaseMetadata):
    """Schema for Math, Physics, Chemistry"""
    category: Literal["stem"] = "stem"
    latex_formula: Optional[str] = Field(None, description="Raw LaTeX string")
    concept_tags: List[str] = Field(default_factory=list, description="Key concepts like 'entropy'")
    difficulty: Optional[str] = Field(None, description="easy, medium, hard")
    is_solution: bool = Field(False, description="Is this a solution/proof?")

class HistoryMetadata(BaseMetadata):
    """Schema for History and Social Sciences"""
    category: Literal["history"] = "history"
    era: Optional[str] = Field(None, description="e.g. Bronze Age, Cold War")
    date_range: Optional[str] = Field(None, description="e.g. 1939-1945")
    key_figures: List[str] = Field(default_factory=list, description="Important people mentioned")
    location: Optional[str] = Field(None, description="Geographic location")
    source_type: Optional[str] = Field(None, description="primary_source, secondary_source")
