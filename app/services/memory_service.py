import os
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from openai import OpenAI

from app.models.artifact import Artifact
from app.infra.artifact_db import ArtifactRepository
from app.schemas import AtomHit
from app.config import get_settings

class MemoryService:
    def __init__(self, repo: ArtifactRepository = None):
        self.repo = repo or ArtifactRepository()
        settings = get_settings()
        self.openai_client = OpenAI(api_key=settings.openai_api_key)

    def _get_embedding(self, text: str) -> List[float]:
        text = text.replace("\n", " ")
        # Using settings or default model
        return self.openai_client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

    def ensure_schema(self):
        """Ensures the DB schema exists."""
        self.repo.ensure_schema()

    def save_artifact(self,
                      profile_id: str,
                      content: str,
                      artifact_type: str = "lesson",
                      summary: str = None,
                      related_book_ids: List[str] = [],
                      topic_tags: List[str] = []) -> Artifact:
        """
        Creates and saves an artifact. Generates embedding from summary (or content if summary is missing).
        """
        text_to_embed = summary if summary else content[:1000] # Fallback to content snippet
        embedding = self._get_embedding(text_to_embed)

        artifact = Artifact(
            id=uuid4(),
            profile_id=profile_id,
            type=artifact_type,
            content=content,
            summary=summary,
            created_at=datetime.utcnow(),
            embedding=embedding,
            related_book_ids=related_book_ids,
            topic_tags=topic_tags
        )

        self.repo.save_artifact(artifact)
        return artifact

    def search_artifacts(self, profile_id: str, query: str = None, limit: int = 5) -> List[AtomHit]:
        """
        Searches for artifacts and returns them as generic AtomHit objects.
        """
        query_embedding = None
        if query:
            query_embedding = self._get_embedding(query)

        artifacts = self.repo.search_artifacts(profile_id, query_embedding, limit)

        hits = []
        for art in artifacts:
            # Map Artifact to AtomHit
            meta_dict = {
                "content_type": art.type,
                "book_id": art.related_book_ids[0] if art.related_book_ids else None,
                "section_title": f"Memory: {art.type}",
                "profile_id": art.profile_id,
                "created_at": str(art.created_at)
            }

            hits.append(AtomHit(
                id=str(art.id),
                content=f"--- PREVIOUS CLASS MEMORY ({art.created_at.strftime('%Y-%m-%d')}) ---\nType: {art.type}\nContent: {art.content}",
                metadata=meta_dict,
                score=1.0 # Placeholder
            ))

        return hits
