from __future__ import annotations

import os
from functools import lru_cache

from openai import AsyncOpenAI, OpenAI

from .config import get_settings


@lru_cache()
def get_sync_client() -> OpenAI:
    """
    Simplified OpenAI client factory.

    Uses OPENAI_API_KEY and optional OPENAI_BASE_URL; no Azure-specific logic.
    """
    settings = get_settings()
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL") or None
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key, base_url=base_url)


@lru_cache()
def get_async_client() -> AsyncOpenAI:
    """
    Async variant for future streaming/chat use.
    """
    settings = get_settings()
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL") or None
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=api_key, base_url=base_url)

