# System Architecture

## Overview

The ESL RAG Backend is designed to ingest educational content (textbooks, PDF documents) and provide a semantic search and question-generation interface. It utilizes a hybrid approach to document parsing and a vector-database-backed retrieval engine.

### Core Components

1.  **FastAPI Service (`app/`)**:
    *   Exposes endpoints for Search (`/search`), Concept Retrieval (`/concept`), Quiz Generation (`/generate/quiz`), and Private Ingestion (`/ingest`).
    *   **RAG Orchestrator**: Bridges the gap between retrieval and generation. It fetches context from the search service and injects it into the generation prompt.

2.  **Ingestion Engine (`ingest/`)**:
    *   **Hybrid Ingestor**:
        *   **Primary**: `Docling` (Local) for fast, structured parsing.
        *   **Fallback**: `LlamaParse` (Cloud) for complex layouts.
        *   **Vision/Handwriting**: `OpenAI VLM` (GPT-4o) for handwritten notes or complex diagrams.
        *   **Book Categorization**: Auto-detects `Language`, `STEM`, or `History` categories to enforce specific Pydantic metadata schemas.
    *   **Structure Nodes**: Maintains the hierarchical structure of books (Units, Lessons) in a relational format.
    *   **Content Atoms**: Granular chunks of text/images stored with vector embeddings for semantic search.

3.  **Vision Enrichment Engine**:
    *   **Async Processing**: Decouples image description from initial ingestion.
    *   **Flow**:
        1. Ingestion creates `image_asset` atoms (raw image references).
        2. Celery worker (`enrich_images_task`) picks up pending images.
        3. `VisionEnricher` sends images to GPT-4o for detailed educational descriptions.
        4. Descriptions are saved as `image_desc` atoms, linked to the original image, enabling semantic search over visual content.

4.  **Curriculum Guard**:
    *   **Logic**: Propagates `sequence_index` from the relational hierarchy (`structure_nodes`) to vector metadata (`content_atoms`).
    *   **Enforcement**: Allows the search API to restrict results to content "learned so far" using LlamaIndex `MetadataFilters` (LTE - Less Than or Equal), preventing future concepts from leaking into current answers.

5.  **Classroom Profiles**:
    *   **Teacher Profiles**: Stores teacher preferences, grade levels, and user details in the `teacher_profiles` table.
    *   **Context Injection**: The `ProfileService` retrieves active profile settings (including `PedagogyConfig`) to customize generation prompts (e.g., adapting tone, style, or specific teaching strategies).

6.  **Curriculum Memory**:
    *   **Artifacts**: Stores generated items (quizzes, lessons) as "Artifacts" in the `class_artifacts` table.
    *   **Memory Service**: Indexes these artifacts using vector embeddings (`pgvector`) to enable semantic search over past teaching material ("What did I teach last week?").
    *   **Hybrid Search**: Combines SQL filtering (by profile, date) with vector similarity search to retrieve relevant past content for cumulative reviews.

7.  **Data Storage (Split Architecture)**:
    *   **Content DB (`db_content`)**:
        *   Read-mostly database for static educational content.
        *   Tables: `structure_nodes` (with `owner_id`), `data_content_atoms` (LlamaIndex managed), `pedagogy_strategies`.
        *   **Unified Content**: Stores both global (public) textbooks and user-uploaded private content. Private content is secured via the `owner_id` column.
    *   **User DB (`db_user`)**:
        *   Read-write database for user-specific data.
        *   Tables: `teacher_profiles`, `class_artifacts`.
    *   **Redis**: Used as the message broker for Celery and result backend for async jobs.

---

## Retrieval & Generation (RAG) Flow

1.  **Curriculum Guard (Filtering)**:
    *   Queries are first filtered by `book_id` and strict curriculum boundaries (e.g., `sequence_index` or `unit`).
    *   **Privacy Guard**: Queries are also filtered by `owner_id` to ensure users only see global content (NULL) or their own private content.
    *   This is enforced using LlamaIndex `MetadataFilters`.
    *   **Optimization**: A specific GIN Index on the `metadata_` column in Postgres is required to ensure these filters remain fast as the dataset grows.

2.  **Vector Search**:
    *   Within the filtered subset, `pgvector` retrieves the most semantically relevant "atoms" (text chunks).

3.  **Context Injection**:
    *   The `rag_engine` orchestrator concatenates these atoms into a source context.
    *   The Generation Service (`generation.py`) instructs the LLM to use this provided context as the primary source material, ensuring the quiz/content is grounded in the textbook.

---

## Production Scaling Strategy

This section outlines how the system is designed to scale to meet the requirements of **1000s of textbooks** and **100s of active users** querying specific books.

### 1. Ingestion Scaling (1000s of Textbooks)

Ingesting thousands of PDFs is a compute-intensive and I/O-heavy process.

*   **Asynchronous Processing Pipeline**:
    *   Ingestion requests should never block the API. We utilize Celery to offload ingestion tasks (`ingest.pipeline.run_ingestion`) to background workers.
    *   **Queue Management**: Use a dedicated Celery queue (e.g., `ingest_queue`) separate from high-priority user tasks (like Quiz Generation). This ensures that a massive ingestion backlog doesn't degrade user experience.

*   **Horizontal Worker Scaling**:
    *   The parsing (Docling/OCR) and embedding (OpenAI) steps are parallelizable at the book level.
    *   Deploy multiple Celery worker instances across different nodes. Since `Docling` runs locally, CPU/RAM resources on workers must be sized according to the complexity of PDFs.

*   **Database Optimization**:
    *   **Batch Inserts**: Ensure `content_atoms` are inserted in batches rather than one by one to reduce round-trips.
    *   **Index Management**: Creating HNSW indexes (used by `pgvector`) is expensive. For bulk ingestion of 1000s of books, it may be efficient to drop the vector index, ingest all data, and rebuild the index, or use partitioning strategies (see below).

### 2. Retrieval Scaling (100s of Users)

While 100s of users is not "web scale", providing low-latency semantic search over a corpus of 1000s of books requires optimization.

*   **Targeted Search (Metadata Filtering)**:
    *   Users typically query *specific* books (e.g., "Show me vocabulary from Book A").
    *   We leverage the `book_id` metadata column in `pgvector`.
    *   **Partitioning**: In a production Postgres setup, we would partition the content table (e.g. `data_content_atoms`) by `book_id` (list partitioning) or hash partitioning. This allows the query planner to scan only the relevant partitions, drastically reducing search time compared to scanning a monolithic index of 1000 books.
    *   **GIN Indexing**: As mentioned, the JSONB metadata column must be GIN-indexed to support rapid filtering on `book_id`, `unit`, and `sequence_index`.

*   **Caching Strategy**:
    *   Implement **Redis Caching** for frequent queries. If multiple students in a class ask "What is the summary of Unit 1?", the embedding generation and DB lookup should only happen once.
    *   Cache keys: `hash(book_id + query_text)`.

*   **Read Replicas**:
    *   If read traffic increases significantly, deploy PostgreSQL Read Replicas. The application can offload `SELECT` queries (searches) to replicas while writes (ingestion) go to the primary.

*   **Embedding Latency**:
    *   The bottleneck for search is often generating the query embedding (OpenAI API call).
    *   To mitigate this, ensure the backend runs in a region with low latency to OpenAI's API, or switch to a high-performance local embedding model (e.g., ONNX runtime) if latency becomes critical.
