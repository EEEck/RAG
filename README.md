# ESL RAG Backend (Local)

Lightweight backend scaffold for the ESL RAG pipeline. Default runtime is Docker + docker-compose (no Azure lock-in).

## Quick start
1) Copy `.env` (already at repo root) and ensure it contains:
   - `OPENAI_API_KEY=...`
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (optional; defaults rag/rag/rag).
2) Build and start:
   ```bash
   docker-compose up --build
   ```
3) Check health:
   ```bash
   curl http://localhost:8000/health
   ```

## Services
- `app`: FastAPI stub (`app/main.py`) ready to host ingestion/retrieval endpoints.
- `db`: Postgres with `pgvector` (`pgvector/pgvector:pg16`).

## Notes
- Azure-specific assets remain isolated under `Azure_template/` and are ignored by Docker builds.
- Ingestion/helpers live under `ingest/`; wire them into FastAPI as endpoints next.

## Development & Notebooks

To run Jupyter notebooks locally while connecting to the Dockerized database and Redis:

1.  **Install Development Dependencies**:
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Start Infrastructure**:
    ```bash
    docker-compose up -d db redis
    ```

3.  **Launch Jupyter**:
    ```bash
    jupyter notebook
    ```

4.  **Notebook Connection Preamble**:
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
