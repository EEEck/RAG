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
    POSTGRES_CONTENT_HOST=db_content
    POSTGRES_USER_HOST=db_user
    ```

### Starting the System
Run the following command in the repository root:

```bash
docker-compose up --build -d
```

This starts:
*   **App Service**: The FastAPI backend (Port 8000).
*   **DB Content Service**: PostgreSQL for Textbooks/Pedagogy (Port 5432).
*   **DB User Service**: PostgreSQL for Profiles/Artifacts (Port 5433).
*   **Redis**: For task queues.
*   **Worker**: Celery worker for background jobs.

Verify the system is running:
```bash
curl http://localhost:8000/health
# Output: {"status":"ok"}
```

## 2. Ingesting Documents

You can ingest documents globally (admin) or privately (teacher).

### Option A: Manual Global Ingestion (Admin)
To add a textbook for **everyone** to use:

1.  Enter the app container:
    ```bash
    docker-compose exec app bash
    ```
2.  Run the ingestion script:
    ```python
    python -m ingest.pipeline
    ```
    *(Note: Modify `ingest/pipeline.py` or use a CLI wrapper to target your specific PDF).*

### Option B: Private Ingestion (Teacher)
Teachers can upload their own content which remains private to them.

**Endpoint:** `POST /ingest`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/ingest/" \
     -F "file=@/path/to/my_private_notes.pdf" \
     -F "user_id=teacher_123"
```
*   **file**: The PDF document.
*   **user_id**: The ID of the teacher. This ensures the content is only searchable by `teacher_123`.

## 3. Managing Classroom Profiles

Classroom profiles allow teachers to persist settings (like grade level and preferred textbook) and pedagogy styles (e.g., "Socratic", "Grammar-focused").

### Creating a Profile
Use the `POST /profiles` endpoint to create a new profile.

**Example Request:**
```json
{
  "user_id": "teacher_123",
  "name": "Grade 5 Science",
  "grade_level": 5,
  "pedagogy": {
    "focus_areas": ["interactive", "visual"],
    "tone": "enthusiastic"
  },
  "content_scope": {
    "book_ids": ["science_book_v1"]
  }
}
```

### Switching Profiles
The frontend or API client should store the `profile_id` returned from creation and pass it to generation endpoints (like `/generate/quiz`) to ensure the AI adapts to the specific classroom context.

## 4. Curriculum Memory (Artifacts)

The system can "remember" what has been taught by saving generated items as **Artifacts**. This enables features like "Review what we learned last week."

### Saving an Artifact
After generating a quiz or lesson plan that you want to keep, send it to `POST /artifacts`.

**Example Request:**
```json
{
  "profile_id": "profile_abc_123",
  "type": "quiz",
  "content": "Question 1: ...",
  "summary": "Quiz on Photosynthesis basics",
  "related_book_ids": ["science_book_v1"]
}
```

### Searching Memory
To find past materials, use `GET /artifacts`.
*   **Filter by Profile**: `?profile_id=...`
*   **Semantic Search**: `?query=photosynthesis` (finds conceptually related past items)
*   **Timeline View**: `GET /artifacts/timeline?start_date=...&end_date=...`

## 5. Monitoring & Management

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

## 6. Troubleshooting

*   **Database Connection Failed**:
    *   Ensure the `db_content` and `db_user` containers are healthy.
    *   Check `.env` credentials match `docker-compose.yml`.
*   **OpenAI Errors**:
    *   Verify `OPENAI_API_KEY` is valid and has credits.
    *   Check `docker-compose logs app` for specific API error messages.
*   **Ingestion Stuck**:
    *   Complex PDFs can take time. Check `worker` logs to see if it's processing or hanging.
    *   If using LlamaParse fallback, ensure `LLAMA_CLOUD_API_KEY` is set.
