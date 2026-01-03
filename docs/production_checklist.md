# Production Readiness Checklist

This checklist is for hardening the MVP demo into a production service.
The architecture is scalable, but these items close the operational gaps.

## Security
- Secrets management (no plaintext `.env` in repo; use a vault).
- AuthN/AuthZ for all endpoints; enforce per-tenant book access.
- Input validation and request size limits on ingestion and generation.
- PII handling policy and data retention (artifacts + logs).

## Data + Migrations
- Schema migrations with versioning (Alembic or similar).
- Explicit initialization for both `db_content` and `db_user`.
- Backups + restore runbooks; automated retention policies.
- GIN/HNSW index creation lifecycle documented and automated.

## Reliability + Scaling
- Worker autoscaling policy (Celery concurrency, queue depth).
- Separate queues for ingestion vs generation; rate limits per tenant.
- Retry policies with exponential backoff and dead-letter queues.
- Circuit breakers for LLM/embedding failures.

## Observability
- Structured logs with request IDs and job IDs.
- Metrics: ingestion time, search latency, token usage, error rates.
- Tracing across API -> worker -> DB -> LLM calls.
- Alerts for queue backlog and DB connection saturation.

## Performance
- Caching policy for repeated queries (Redis).
- Batch ingestion + embedding pipeline (avoid single-row inserts).
- Data partitioning strategy ready for large book counts.
- Load testing for search + generation endpoints.

## Release + Ops
- CI pipeline with unit/integration tests.
- Deployment pipeline with rollback (blue/green or canary).
- Infra as code (Dockerfiles, compose for local; IaC for prod).
- Runbooks for incident response and key rotations.

## Compliance + Governance
- Content safety policy and audit trail for generated items.
- Guardrails for curriculum filters (`sequence_index` enforcement).
- User data export/delete operations.
