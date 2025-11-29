# ESL RAG Backend (Local)

Lightweight backend scaffold for the ESL RAG pipeline. Designed for educational content ingestion, semantic search, and quiz generation using a hybrid database architecture (Postgres Relational + Vector).

## Key Features

*   **Hybrid Ingestion Engine**:
    *   **Docling (Local)**: Fast, structured parsing for standard PDFs.
    *   **LlamaParse (Cloud)**: Fallback for complex layouts.
    *   **Vision Enrichment**: Automatically describes images using GPT-4o via an async Celery pipeline.
*   **Curriculum Guard**:
    *   Enforces "learned so far" constraints.
    *   Filters search results based on the student's current progress in the book (`sequence_index`).
*   **Strict Metadata Schemas**:
    *   Auto-detects book category (`Language`, `STEM`, `History`).
    *   Enforces Pydantic schemas to ensure clean, structured metadata.
*   **Scalable Architecture**:
    *   PostgreSQL with `pgvector` for vector search.
    *   Celery + Redis for asynchronous background tasks (ingestion, enrichment).

## Quick Start (Docker)

1.  **Environment Setup**:
    Copy `.env` (already at repo root) and ensure it contains:
    ```bash
    OPENAI_API_KEY=sk-...
    POSTGRES_USER=rag
    POSTGRES_PASSWORD=rag
    POSTGRES_DB=rag
    ```

2.  **Build and Start**:
    ```bash
    docker-compose up --build
    ```

3.  **Check Health**:
    ```bash
    curl http://localhost:8000/health
    ```

## Development & Notebooks

To run Jupyter notebooks locally while connecting to the Dockerized database and Redis:

1.  **Install Development Dependencies**:
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Start Infrastructure**:
    Start only the database and redis services (skip the app/worker if you are running code locally):
    ```bash
    docker-compose up -d db redis
    ```

3.  **Start Celery Worker (Optional)**:
    If you are testing the full pipeline including Vision Enrichment, you need a worker running:
    ```bash
    # Make sure you are in the repo root
    celery -A app.celery_worker worker --loglevel=info
    ```

4.  **Launch Jupyter**:
    ```bash
    jupyter notebook
    ```

5.  **Notebook Connection Preamble**:
    To ensure your local notebook connects to the exposed Docker ports (localhost) instead of trying to resolve internal service names, add this code block at the top of your notebook:

    ```python
    import os
    from dotenv import load_dotenv

    # Load secrets (API keys)
    load_dotenv()

    # Override infrastructure hosts for local execution
    # This ensures we talk to localhost:5432 and localhost:6379
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["REDIS_HOST"] = "localhost"
    ```

## Services Structure
- `app/`: FastAPI application and API endpoints.
- `ingest/`: Ingestion logic, parsing, and database interaction.
- `docs/`: Architecture and design documentation (MkDocs).
- `data/`: Local data folder for raw PDFs.

## Testing

Run the full test suite with coverage:
```bash
pytest --cov=app --cov=ingest
```
