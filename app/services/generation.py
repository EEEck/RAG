from __future__ import annotations

import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

from ..config import get_settings
from ..agent_factory import create_agent
from ..schemas import (
    GenerateItemsRequest,
    GenerateItemsResponse,
    GeneratedItem,
    ScopeReport,
    PedagogyConfig,
)
from pydantic import BaseModel

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
        ),
        "stem": (
            "You are a STEM content creator (Math/Science). "
            "Generate problems or conceptual questions based on the provided context. "
            "Focus on testing understanding of the core concepts found in the source material. "
        ),
        "history": (
            "You are a History assessment writer. "
            "Generate questions based on the provided historical context. "
            "Focus on dates, key figures, and cause-effect relationships described in the text. "
        )
    }

    @classmethod
    def get_prompt(cls, category: str, pedagogy: PedagogyConfig = None) -> str:
        base_prompt = cls._PROMPTS.get(category.lower(), cls._PROMPTS["language"])

        if pedagogy:
            pedagogy_instructions = []
            if pedagogy.tone and pedagogy.tone != "neutral":
                pedagogy_instructions.append(f"Tone: {pedagogy.tone}.")
            if pedagogy.style and pedagogy.style != "standard":
                pedagogy_instructions.append(f"Style: {pedagogy.style}.")
            if pedagogy.focus_areas:
                pedagogy_instructions.append(f"Focus Areas: {', '.join(pedagogy.focus_areas)}.")
            if pedagogy.adaptation_level and pedagogy.adaptation_level != "standard":
                pedagogy_instructions.append(f"Adaptation Level: {pedagogy.adaptation_level}.")

            if pedagogy_instructions:
                base_prompt += "\n\n### PEDAGOGY INSTRUCTIONS ###\n" + "\n".join(pedagogy_instructions)

        return base_prompt

# --- Generation Service ---

class GeneratedItemList(BaseModel):
    items: List[GeneratedItem]

def _extract_items(result: object) -> List[GeneratedItem]:
    payload = None
    for attr in ("data", "output", "result"):
        if hasattr(result, attr):
            payload = getattr(result, attr)
            break
    if payload is None:
        raise AttributeError("Agent result has no data/output/result attribute")

    if isinstance(payload, GeneratedItemList):
        return payload.items
    if isinstance(payload, dict) and "items" in payload:
        return payload["items"]
    if isinstance(payload, list):
        return payload
    if hasattr(payload, "items"):
        return payload.items
    raise ValueError("Agent result payload does not contain items")

def generate_items(req: GenerateItemsRequest, pedagogy_config: PedagogyConfig = None) -> GenerateItemsResponse:
    """
    Use an LLM to generate items constrained by the given concept pack or provided context.
    """
    # 1. Select System Prompt
    system_prompt = PromptFactory.get_prompt(req.category, pedagogy_config)

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

    prompt_content = f"Create {req.count} items. " \
                     f"Each item must have: stem, options (or null), answer, concept_tags (list), uses_image (bool). " \
                     f"Here is the spec:\n{json.dumps(user_payload, ensure_ascii=False)}"

    # 3. Append RAG Context
    if req.context_text:
        prompt_content += f"\n\n### SOURCE MATERIAL (CONTEXT) ###\nUse the following text as the primary source for the content:\n\n{req.context_text}"

    # 4. Create Agent & Call
    # We use GeneratedItemList to ensure we get a list wrapped in an object, which is usually more robust for tool calling.
    try:
        agent = create_agent(result_type=GeneratedItemList, system_prompt=system_prompt)
        try:
            asyncio.get_running_loop()
            use_thread = True
        except RuntimeError:
            use_thread = False

        if use_thread:
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = executor.submit(agent.run_sync, prompt_content).result()
        else:
            result = agent.run_sync(prompt_content)
        items = _extract_items(result)
    except Exception as e:
        print(f"Generation failed: {e}")
        return GenerateItemsResponse(items=[], scope_report=ScopeReport(violations=0, notes=[f"Error: {str(e)}"]))

    report = ScopeReport(violations=0, notes=[])
    return GenerateItemsResponse(items=items, scope_report=report)
