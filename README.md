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
