from __future__ import annotations

import os

from openai import OpenAI

from app import openai_client


def test_get_sync_client_uses_env_key(monkeypatch):
    openai_client.get_sync_client.cache_clear()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = openai_client.get_sync_client()
    assert isinstance(client, OpenAI)
