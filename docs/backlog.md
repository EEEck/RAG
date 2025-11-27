# Backlog & Status

## Docker & Infra
- [x] Local Dockerfile + docker-compose (app + pgvector) using `.env` for secrets.
- [ ] Add image build cache optimization (multi-stage, slim runtime).
- [ ] Wire migration/seed command for Postgres (pgvector extension check).

## Ingestion & Data
- [ ] CLI entrypoint to run Docling parse + lesson/vocab ingestion into Postgres.
- [ ] Unit/lesson segmentation rule tuning per textbook.
- [ ] Vocab-at-end linking verification across books.

## Retrieval / API
- [x] Add FastAPI endpoints for lesson search and vocab search (uses pgvector).
- [x] Add concept-pack builder and scope-aware query path.
- [ ] Reranker integration for short queries.

## Users & Persistence
- [ ] Add user store (accounts, saved textbooks, saved queries).
- [ ] AuthN (token) + simple rate limiting.
- [ ] Teacher profile persistence and lesson selection history.

## Observability & Ops
- [ ] Logging/metrics middleware; request IDs.
- [ ] Basic E2E test in CI (docker-compose up, smoke test /health).
- [ ] Remove remaining Azure-specific hooks; keep template folder optional.

## Testing & QA
- [ ] Expand pytest coverage for ingestion (Docling parse, segmentation, vocab link) and API routes (/search, /concept/*).
- [ ] Add coverage run target (e.g., `pytest --cov=app --cov=ingest`) and track % in CI.
- [ ] Add DB-backed test fixtures (spinning pgvector via docker-compose) for search/concept-pack.
- [ ] Stub LLM calls in tests via responses/mocking to make generation deterministic.

## Frontend (later)
- [ ] Hook frontend to FastAPI (/concept-pack, /generate-items).
- [ ] Add PDF export and item editor.
