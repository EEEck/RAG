from __future__ import annotations

import os
import shutil
import uuid
import tempfile
from pathlib import Path
from typing import Annotated, Dict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks

from ingest.service import IngestionService
from ingest.infra.postgres import PostgresStructureNodeRepository
from ingest.hybrid_ingestor import HybridIngestor

router = APIRouter(prefix="/ingest", tags=["ingest"])

def get_ingestion_service() -> IngestionService:
    """Factory for IngestionService using production dependencies."""
    repo = PostgresStructureNodeRepository()
    # HybridIngestor is the default
    ingestor = HybridIngestor()
    # vector_store will be initialized inside the service using defaults (PGVectorStore)
    return IngestionService(structure_repo=repo, ingestor=ingestor)

@router.post("")
async def ingest_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    background_tasks: BackgroundTasks = None
) -> Dict[str, str]:
    """
    Uploads a file and ingests it into the system, linked to the provided user_id.

    Args:
        file (UploadFile): The PDF or supported file to ingest.
        user_id (str): The ID of the user who owns this content.
        background_tasks (BackgroundTasks): (Optional) Tasks to run after response.

    Returns:
        Dict[str, str]: Status message and the new Book ID.
    """

    # Validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing.")

    # Create a temp file
    # We use delete=False so we can close it and let the service read it, then clean up.
    try:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    try:
        service = get_ingestion_service()
        book_id = uuid.uuid4()

        # Run ingestion synchronously for MVP as requested.
        # This might take time for large files.
        service.ingest_book(
            file_path=tmp_path,
            book_id=book_id,
            owner_id=user_id
        )

        return {
            "status": "success",
            "message": "File ingested successfully.",
            "book_id": str(book_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
