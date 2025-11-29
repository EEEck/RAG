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
    Use an LLM to generate ESL items constrained by the given concept pack or provided context.
    """
    settings = get_settings()
    client = get_sync_client()

    system_prompt = (
        "You are an ESL item writer. "
        "Generate short-answer, cloze, or multiple-choice items "
        "using ONLY the allowed vocabulary and grammar rules provided, "
        "or the provided context text if available. "
        "Return strictly valid JSON."
    )

    # Build the payload, optionally including the RAG context
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

    # Append Context if provided
    if req.context_text:
        prompt_content += f"\n\n### SOURCE MATERIAL (CONTEXT) ###\nUse the following text as the primary source for the content:\n\n{req.context_text}"

    # Note: Using standard OpenAI chat completion API structure.
    # The previous code seemed to use a non-standard `client.responses.create` or a wrapper.
    # Assuming standard OpenAI client usage here based on `openai_client.py`.
    # However, looking at `generation.py` before, it used `client.responses.create`.
    # Checking `openai_client.py`: it returns `OpenAI` instance. Standard usage is `client.chat.completions.create`.
    # I will correct this to use standard `client.chat.completions.create` assuming `client` is a standard `OpenAI` object.

    completion = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_content},
        ],
        response_format={"type": "json_object"},
    )

    text = completion.choices[0].message.content
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return GenerateItemsResponse(items=[], scope_report=ScopeReport(violations=0, notes=["Failed to parse JSON"]))

    raw_items = payload.get("items", [])
    items: List[GeneratedItem] = []
    for obj in raw_items:
        try:
            items.append(GeneratedItem.model_validate(obj))
        except Exception:
            continue

    report = ScopeReport(violations=0, notes=[])
    return GenerateItemsResponse(items=items, scope_report=report)
