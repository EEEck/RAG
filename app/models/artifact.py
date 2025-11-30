from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class Artifact(BaseModel):
    """
    Represents a generated item (Quiz, Lesson) saved as a memory artifact.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    profile_id: str  # MVP: Simple string/UUID
    type: Literal["quiz", "lesson", "summary"]
    content: str  # The actual text content
    summary: Optional[str] = None  # Short summary for embedding/search
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None # Vector embedding of the summary/content

    # Metadata for filtering
    related_book_ids: List[str] = Field(default_factory=list)
    topic_tags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
