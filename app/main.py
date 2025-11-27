from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI

from .config import get_settings
from .routes import search, concept

# Load environment variables (expects OPENAI_API_KEY, PG creds in .env)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="ESL RAG Backend", version="0.1.0")
app.include_router(search.router)
app.include_router(concept.router)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config_preview() -> Dict[str, str | None]:
    settings = get_settings()
    return {
        "openai_key_present": "true" if os.getenv("OPENAI_API_KEY") else "false",
        "postgres_dsn": settings.pg_dsn,
        "embed_model": settings.embed_model,
    }
