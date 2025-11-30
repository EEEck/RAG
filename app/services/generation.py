from __future__ import annotations

import json
from typing import List, Dict

from ..config import get_settings
from ..openai_client import get_sync_client
from ..schemas import (
    GenerateItemsRequest,
    GenerateItemsResponse,
    GeneratedItem,
    ScopeReport,
)

# --- Prompt Factory ---

class PromptFactory:
    """
    Manages system prompts for different domains.
    """
    _PROMPTS = {
        "language": (
            "You are an ESL item writer. "
            "Generate short-answer, cloze, or multiple-choice items "
            "using ONLY the allowed vocabulary and grammar rules provided, "
            "or the provided context text if available. "
            "Return strictly valid JSON."
        ),
        "stem": (
            "You are a STEM content creator (Math/Science). "
            "Generate problems or conceptual questions based on the provided context. "
            "Focus on testing understanding of the core concepts found in the source material. "
            "Return strictly valid JSON."
        ),
        "history": (
            "You are a History assessment writer. "
            "Generate questions based on the provided historical context. "
            "Focus on dates, key figures, and cause-effect relationships described in the text. "
            "Return strictly valid JSON."
        )
    }

    @classmethod
    def get_prompt(cls, category: str) -> str:
        return cls._PROMPTS.get(category.lower(), cls._PROMPTS["language"])

# --- Generation Service ---

def generate_items(req: GenerateItemsRequest) -> GenerateItemsResponse:
    """
    Use an LLM to generate items constrained by the given concept pack or provided context.
    """
    settings = get_settings()
    client = get_sync_client()

    # 1. Select System Prompt
    system_prompt = PromptFactory.get_prompt(req.category)

    # 2. Build User Payload
    user_payload = {
        "textbook_id": req.textbook_id,
        "lesson_code": req.lesson_code,
        "difficulty": req.difficulty,
        "item_types": req.item_types,
        "count": req.count,
        "concept_pack": {
            "vocab": req.concept_pack.vocab,
            "grammar_rules": req.concept_pack.grammar_rules,
            "themes": req.concept_pack.themes,
        },
    }

    prompt_content = f"Create {req.count} items as JSON list under key 'items'. " \
                     f"Each item must have: stem, options (or null), answer, concept_tags (list), uses_image (bool). " \
                     f"Here is the spec:\n{json.dumps(user_payload, ensure_ascii=False)}"

    # 3. Append RAG Context
    if req.context_text:
        prompt_content += f"\n\n### SOURCE MATERIAL (CONTEXT) ###\nUse the following text as the primary source for the content:\n\n{req.context_text}"

    # 4. Call LLM
    try:
        completion = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_content},
            ],
            response_format={"type": "json_object"},
        )
        text = completion.choices[0].message.content
        payload = json.loads(text)
    except Exception as e:
        # Graceful failure
        print(f"Generation failed: {e}")
        return GenerateItemsResponse(items=[], scope_report=ScopeReport(violations=0, notes=[f"Error: {str(e)}"]))

    # 5. Parse Response
    raw_items = payload.get("items", [])
    items: List[GeneratedItem] = []
    for obj in raw_items:
        try:
            items.append(GeneratedItem.model_validate(obj))
        except Exception:
            continue

    report = ScopeReport(violations=0, notes=[])
    return GenerateItemsResponse(items=items, scope_report=report)
