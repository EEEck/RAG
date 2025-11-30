from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Dict, Union

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from celery.result import AsyncResult

from .config import get_settings
from .routes import search, concept, profiles
from .celery_worker import generate_quiz_task

# Load environment variables (expects OPENAI_API_KEY, PG creds in .env)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="ESL RAG Backend", version="0.1.0")
app.include_router(search.router)
app.include_router(concept.router)
app.include_router(profiles.router)


class QuizRequest(BaseModel):
    """
    Request model for quiz generation.

    Attributes:
        book_id (str): The unique identifier of the book.
        unit (int): The unit number.
        topic (str): The topic of the quiz.
    """
    book_id: str
    unit: int
    topic: str


@app.post("/generate/quiz")
async def start_quiz_generation(req: QuizRequest) -> Dict[str, str]:
    """
    Starts a background Celery task to generate a quiz.

    Args:
        req (QuizRequest): The request payload containing book_id, unit, and topic.

    Returns:
        Dict[str, str]: A dictionary containing the task ID and status.
    """
    # We generate a UUID for the job context, but we return the Celery task ID
    user_job_id = str(uuid.uuid4())
    task = generate_quiz_task.delay(user_job_id, req.book_id, req.unit, req.topic)
    return {"job_id": task.id, "status": "queued"}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Union[str, Dict]]:
    """
    Retrieves the status of a background job.

    Args:
        job_id (str): The ID of the Celery task.

    Returns:
        Dict[str, Union[str, Dict]]: The status of the job, and the result data if complete.
    """
    result = AsyncResult(job_id, app=generate_quiz_task.app)
    if result.state == 'PENDING':
        return {"status": "processing"}
    elif result.state == 'SUCCESS':
        return {"status": "complete", "data": result.result}
    elif result.state == 'FAILURE':
        return {"status": "failed", "error": str(result.result)}
    else:
        return {"status": result.state}


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Health check endpoint to verify service status.

    Returns:
        Dict[str, str]: {"status": "ok"} if running.
    """
    return {"status": "ok"}


@app.get("/config")
def config_preview() -> Dict[str, str | None]:
    """
    Endpoint to preview current configuration (safely).

    Returns:
        Dict[str, str | None]: Configuration details like OpenAI key presence and Postgres DSN.
    """
    settings = get_settings()
    return {
        "openai_key_present": "true" if os.getenv("OPENAI_API_KEY") else "false",
        "postgres_dsn": settings.pg_dsn,
        "embed_model": settings.embed_model,
    }
