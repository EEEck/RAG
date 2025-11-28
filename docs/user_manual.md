# User Manual (Operator Guide)

This guide describes how to operate the ESL RAG Backend, including starting services, running ingestion, and troubleshooting.

## 1. Getting Started

### Prerequisites
*   Docker & Docker Compose installed.
*   `.env` file created in the root directory with:
    ```bash
    OPENAI_API_KEY=sk-...
    POSTGRES_USER=rag
    POSTGRES_PASSWORD=rag
    POSTGRES_DB=rag
    ```

### Starting the System
Run the following command in the repository root:

```bash
docker-compose up --build -d
```

This starts:
*   **App Service**: The FastAPI backend (Port 8000).
*   **DB Service**: PostgreSQL with pgvector (Port 5432).
*   **Redis**: For task queues.
*   **Worker**: Celery worker for background jobs.

Verify the system is running:
```bash
curl http://localhost:8000/health
# Output: {"status":"ok"}
```

## 2. Ingesting Documents

Ingestion is currently triggered via script or code (API endpoint for ingestion is pending in `main.py`).

**To run ingestion manually:**

1.  Enter the app container (or run locally if Python env is set up):
    ```bash
    docker-compose exec app bash
    ```
2.  Run the ingestion script:
    ```python
    python -m ingest.pipeline
    ```
    *(Note: You may need to modify the `__main__` block in `ingest/pipeline.py` or use a custom script to point to your specific PDF file).*

## 3. Monitoring & Management

### Checking Async Jobs (Quizzes)
When a user requests a quiz, a Job ID is returned. Check status via:
`GET /jobs/{job_id}`

### Logs
To view logs for troubleshooting:
```bash
# All logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f app
docker-compose logs -f worker
```

## 4. Troubleshooting

*   **Database Connection Failed**:
    *   Ensure the `db` container is healthy.
    *   Check `.env` credentials match `docker-compose.yml`.
*   **OpenAI Errors**:
    *   Verify `OPENAI_API_KEY` is valid and has credits.
    *   Check `docker-compose logs app` for specific API error messages.
*   **Ingestion Stuck**:
    *   Complex PDFs can take time. Check `worker` logs to see if it's processing or hanging.
    *   If using LlamaParse fallback, ensure `LLAMA_CLOUD_API_KEY` is set.
