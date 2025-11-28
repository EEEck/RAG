# Project Analysis & Backlog

## Current State Analysis
*   **Ingestion:** `HybridIngestor` (Docling + LlamaParse) is implemented in `ingest/hybrid_ingestor.py`.
*   **Database:** `structure_nodes` (manual) and `content_atoms` (managed by LlamaIndex `PGVectorStore`). Partitioning logic simplified to metadata filtering.
*   **Embeddings:** Configured for OpenAI (`text-embedding-3-small`, 1536 dim) via LlamaIndex.
*   **API:** Async endpoints (`/generate/quiz`) and Celery worker (`app/celery_worker.py`) are set up.
*   **Infrastructure:** `docker-compose.yml` includes Redis and Celery services.

## Gap Analysis (Required vs. Existing)
| Feature | Feature | Current | Required | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Schema** | `structure_nodes`, `content_atoms` (LlamaIndex) | `structure_nodes`, `content_atoms` (partitioned) | 🟢 Done (Simplified) |
| **Ingestion** | `HybridIngestor` class | Docling (PDF) -> Check -> LlamaParse (Fallback) | 🟢 Done |
| **Search** | LlamaIndex / OpenAI (1536) | Gemini Flash (768) | 🟡 Switch Provider (OpenAI active) |
| **Async** | Celery + Redis | Celery + Redis | 🟢 Done |
| **Curriculum**| Basic filtering | Strict `sequence_index` enforcement | 🟡 Partial |

## Parallelizable Work Streams
1.  **Database & Schema Foundation:**
    *   Setup PostgreSQL partitioning. (Replaced with LlamaIndex schema)
    *   Implement `structure_nodes` and `content_atoms` DDL. (Done)
    *   Create `create_book_partition` function. (Removed)

2.  **Ingestion Engine:**
    *   Implement `HybridIngestor` class. (Done)
    *   Integrate `docling` library and `llama_parse`. (Done)
    *   Implement "Router Logic" for quality gating. (Done)

3.  **Infrastructure & API:**
    *   Add Redis to Docker Compose. (Done)
    *   Setup Celery worker structure. (Done)
    *   Draft Async API endpoints (`/generate/quiz`). (Done)

## Next Steps (Week 2 Priorities)
1.  **Enrichment Engine:**
    *   Implement Database Persistence (Insert Logic). (🟢 Done via LlamaIndex)
    *   Implement End-to-End Pipeline (Notebook/Script). (🟢 Done)
    *   Implement Vision AI (Image description). (🔴 Pending)
    *   Switch to Real Embeddings (Gemini/OpenAI). (🟢 Done - OpenAI)
2.  **Curriculum Guard:** Implement the SQL query logic for `retrieve_and_generate`.
3.  **LLM Switch:** Move from OpenAI to Gemini Flash (if desired).

## Recent Updates
*   **Vector Database Integration:** Replaced manual `pgvector` logic with **LlamaIndex** (`PGVectorStore`).
    *   Simplified `content_atoms` schema (removed strict partitioning in favor of metadata filtering).
    *   Unified embedding generation (OpenAI) and persistence.
*   **Testing:** Verified pipeline with mocked LlamaIndex components.
