from __future__ import annotations

import json
from typing import List

from ..config import get_settings
from ..openai_client import get_sync_client
from ..schemas import (
    ConceptPack,
    GenerateItemsRequest,
    GenerateItemsResponse,
    GeneratedItem,
    ScopeReport,
)


def generate_items(req: GenerateItemsRequest) -> GenerateItemsResponse:
    """
    Use an LLM to generate ESL items constrained by the given concept pack.
    """
    settings = get_settings()
    client = get_sync_client()

    system_prompt = (
        "You are an ESL item writer. "
        "Generate short-answer, cloze, or multiple-choice items "
        "using ONLY the allowed vocabulary and grammar rules provided. "
        "Return strictly valid JSON."
    )

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

    completion = client.responses.create(
        model=settings.chat_model,
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Create {req.count} items as JSON list under key 'items'. "
                f"Each item must have: stem, options (or null), answer, concept_tags (list), uses_image (bool). "
                f"Here is the spec:\n{json.dumps(user_payload, ensure_ascii=False)}",
            },
        ],
        response_format={"type": "json_object"},
    )

    text = completion.output[0].content[0].text
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: no items
        return GenerateItemsResponse(items=[], scope_report=ScopeReport(violations=0, notes=["Failed to parse JSON"]))

    raw_items = payload.get("items", [])
    items: List[GeneratedItem] = []
    for obj in raw_items:
        try:
            items.append(GeneratedItem.model_validate(obj))
        except Exception:
            continue

    # Simple scope report placeholder; real scope-check could be added later
    report = ScopeReport(violations=0, notes=[])
    return GenerateItemsResponse(items=items, scope_report=report)

