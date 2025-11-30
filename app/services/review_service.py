from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timedelta

from app.services.memory_service import MemoryService
from app.services.search_service import get_search_service, SearchService
from app.services.generation import generate_items
from app.schemas import GenerateItemsRequest, GenerateItemsResponse, ConceptPack, PedagogyConfig, ScopeReport
from app.services.profile_service import get_profile_service

class ReviewService:
    def __init__(self, memory_service: MemoryService = None, search_service: SearchService = None):
        self.memory_service = memory_service or MemoryService()
        self.search_service = search_service or get_search_service()

    def generate_review_quiz(
        self,
        profile_id: str,
        time_window: str = "last_7_days",
        custom_date_range: tuple[datetime, datetime] | None = None,
        count: int = 5
    ) -> GenerateItemsResponse:
        """
        Generates a review quiz based on artifacts created within a specific time window.
        """
        # 1. Determine Date Range
        if custom_date_range:
            start_date, end_date = custom_date_range
        else:
            end_date = datetime.utcnow()
            if time_window == "last_7_days":
                start_date = end_date - timedelta(days=7)
            elif time_window == "last_30_days":
                start_date = end_date - timedelta(days=30)
            else:
                # Default to 7 days
                start_date = end_date - timedelta(days=7)

        # 2. Fetch Artifacts
        artifacts = self.memory_service.get_artifacts_in_range(profile_id, start_date, end_date)

        if not artifacts:
            # Fallback: If no artifacts, maybe just generate a generic review or return empty?
            # For now, let's return a "no content" response or similar.
            # But the signature demands GenerateItemsResponse.
            # We'll try to find *any* recent stuff or just fail gracefully.
            return GenerateItemsResponse(items=[], scope_report=ScopeReport(violations=0, notes=["No artifacts found in range"]))

        # 3. Extract Topics
        topics = set()
        categories = set()
        context_parts = []

        context_parts.append(f"### REVIEW MATERIAL ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ###")

        for art in artifacts:
            # Collect topics
            if art.topic_tags:
                topics.update(art.topic_tags)

            # Collect content summaries
            summary_text = art.summary if art.summary else art.content[:500] + "..."
            tags_display = ', '.join(art.topic_tags or [])
            context_parts.append(f"--- Lesson/Quiz from {art.created_at.strftime('%Y-%m-%d')} ---\nType: {art.type}\nTopics: {tags_display}\nSummary: {summary_text}")

            # Infer category (simplistic)
            # Ideally artifacts would store 'category' (STEM, History, Language)
            # For now, we default to language unless we see cues, or we just pick one.
            # But generate_items needs a category. Let's assume 'language' or pick from first artifact if available?
            # Artifact model doesn't strictly have 'category' field, it has 'type' (quiz/lesson).
            # We might need to guess or pass it in. defaulting to "language".
            categories.add("language")

        topics_list = list(topics)
        combined_query = " ".join(topics_list)

        # 4. Re-query Textbook RAG (Optional but recommended to get fresh context)
        # We only search if we have topics.
        if combined_query:
            search_response = self.search_service.search_content(query=combined_query, limit=5)
            if search_response.atoms:
                context_parts.append("\n### TEXTBOOK REFERENCE MATERIAL ###")
                for atom in search_response.atoms:
                    context_parts.append(f"--- Reference ---\n{atom.content}")

        full_context = "\n\n".join(context_parts)

        # 5. Fetch Profile for Pedagogy
        profile_service = get_profile_service()
        profile = profile_service.get_profile(profile_id)
        pedagogy_config = profile.pedagogy_config if profile else None

        # 6. Generate Review
        # We use a special "review" category or just "language" with a custom prompt?
        # The prompt factory has "language", "stem", "history".
        # We'll use "language" for now as default, but ideally we'd know the domain.

        req = GenerateItemsRequest(
            textbook_id="review-session", # Placeholder
            lesson_code="Review",
            concept_pack=ConceptPack(vocab=[], themes=topics_list),
            count=count,
            context_text=full_context,
            category="language", # TODO: Dynamic category
            profile_id=profile_id,
            use_memory=True
        )

        return generate_items(req, pedagogy_config=pedagogy_config)
