# Project Analysis & Backlog

## Current State Analysis
*   **Ingestion:** `HybridIngestor` (Docling + LlamaParse) is implemented in `ingest/hybrid_ingestor.py`.
*   **Database:** `structure_nodes` and `content_atoms` schema with partitioning is defined and applied.
*   **Embeddings:** Configured for OpenAI (`text-embedding-3-large`, 1536 dim) as per current constraint, pending switch to Gemini.
*   **API:** Async endpoints (`/generate/quiz`) and Celery worker (`app/celery_worker.py`) are set up.
*   **Infrastructure:** `docker-compose.yml` includes Redis and Celery services.

## Gap Analysis (Required vs. Existing)
| Feature | Current | Required | Status |
| :--- | :--- | :--- | :--- |
| **Schema** | `structure_nodes`, `content_atoms` (partitioned) | `structure_nodes`, `content_atoms` (partitioned) | 🟢 Done |
| **Ingestion** | `HybridIngestor` class | Docling (PDF) -> Check -> LlamaParse (Fallback) | 🟢 Done |
| **Search** | OpenAI (1536) | Gemini Flash (768) | 🔴 Switch Provider |
| **Async** | Celery + Redis | Celery + Redis | 🟢 Done |
| **Curriculum**| Basic filtering | Strict `sequence_index` enforcement | 🟡 Partial |

## Parallelizable Work Streams
1.  **Database & Schema Foundation:**
    *   Setup PostgreSQL partitioning. (Done)
    *   Implement `structure_nodes` and `content_atoms` DDL. (Done)
    *   Create `create_book_partition` function. (Done)

2.  **Ingestion Engine:**
    *   Implement `HybridIngestor` class. (Done)
    *   Integrate `docling` library and `llama_parse`. (Done)
    *   Implement "Router Logic" for quality gating. (Done)

3.  **Infrastructure & API:**
    *   Add Redis to Docker Compose. (Done)
    *   Setup Celery worker structure. (Done)
    *   Draft Async API endpoints (`/generate/quiz`). (Done)

## Next Steps (Week 2 Priorities)
1.  **Enrichment Engine:** Implement Vision AI (Image description) and Embedding generation logic (using `HybridIngestor` output).
2.  **Curriculum Guard:** Implement the SQL query logic for `retrieve_and_generate`.
3.  **LLM Switch:** Move from OpenAI to Gemini Flash.
