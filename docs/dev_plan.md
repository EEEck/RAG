# Development Plan & Architectural Decisions
# **Project: Scalable Textbook RAG (MVP)**

**Timeline:** 4 Weeks

**Goal:** Deploy a production-ready RAG system that ingests ESL/Science textbooks, enforces strict curriculum safety (Unit 1 concepts only), and scales to 100+ concurrent users via database partitioning.

## **1\. Core User Stories**

| Actor | Story | Acceptance Criteria |
| :---- | :---- | :---- |
| **Admin** | As an admin, I want to upload a PDF (e.g., "Green Line 1") and have it automatically ingested, partitioned, and indexed. | System ingests book, populates vectors via LlamaIndex, storing book_id in metadata. |
| **Teacher** | As a teacher, I want to generate a quiz for **Unit 3** that *only* uses vocabulary/grammar from Units 1-3. | API query includes filter unit_id <= 3. Result contains zero concepts from Unit 4+. |
| **Teacher** | As a teacher, I want to select my specific textbook profile so I don't get search results from unrelated books. | API requests are filtered by book_id metadata. |
| **System** | As a platform, I need to handle 100 teachers clicking "Generate" simultaneously without crashing. | Requests are queued via Celery/Redis; Users receive a job_id and poll for results. |

## **2\. High-Level Architecture**

### **The Stack**

* **Ingestion:** Python Worker (Docling for layout + LlamaParse for complex fallback).
* **Vector Store:** **LlamaIndex** + `PGVectorStore` (PostgreSQL).
* **Database:** PostgreSQL 16+ (Managed).
* **API Layer:** FastAPI (Async).  
* **Async Queue:** Redis (Broker) + Celery (Workers).
* **Caching:** Redis (Semantic Cache).  
* **LLM:** OpenAI / Gemini.

## **3\. The Universal Database Schema (LlamaIndex Adapted)**

*Updated strategy: Use LlamaIndex managed tables for content, metadata for partitioning.*

\-- Enable Extensions  
CREATE EXTENSION IF NOT EXISTS vector;

\-- 1\. Structure Nodes (The Table of Contents)  
\-- Stores the hierarchy: Book -> Unit -> Lesson -> Exercise
CREATE TABLE structure_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL,
    parent_id UUID REFERENCES structure_nodes(id),
    node_level INTEGER, -- 0=Book, 1=Unit, 2=Section
    title TEXT,  
    sequence_index INTEGER, -- Vital for "Curriculum Safety" (Unit 1 < Unit 2)
    meta_data JSONB -- {"page_start": 10, "page_end": 12}
);

\-- 2\. Content Atoms (LlamaIndex Managed)
\-- LlamaIndex creates/manages the 'content_atoms' table (or similar name).
\-- Key columns: id, text, metadata, embedding.
\-- 'book_id', 'node_id', 'atom_type' are stored in the 'metadata' JSONB column.

## **4\. The Hybrid Ingestion Pipeline (Python)**

This router logic handles the "Clean Layout" vs. "Complex Syntax" trade-off.

*(See `ingest/hybrid_ingestor.py` and `ingest/pipeline.py` for implementation)*

## **5\. API & Scaling Architecture**

To handle "Thundering Herds" (30 teachers clicking 'Generate' at once), we use an Asynchronous Queue pattern.

### **The Stack Implementation**

1. **FastAPI** receives the request.  
2. **Redis** stores the job status (pending).  
3. **Celery Worker** picks up the heavy RAG task.  
4. **Frontend** polls /job/{id} every 2 seconds.

## Curriculum Guard (Sequence Index Filtering)

### Context
Teachers need to generate quizzes or retrieve content restricted to what has been taught so far. Content is organized hierarchically (Units, Lessons) and has a sequential order (`sequence_index`).

### Solution
We implement a "Curriculum Guard" by strictly filtering search results based on the `sequence_index`.

### Implementation Details
1.  **Ingestion:**
    *   The `sequence_index` from `StructureNode` (relational DB) is denormalized and propagated to the metadata of `ContentAtom` (Vector DB) during ingestion.
    *   This enables efficient filtering directly within the vector search engine without complex cross-database joins.

2.  **Search (LlamaIndex):**
    *   We use LlamaIndex's `MetadataFilters`.
    *   When a search request includes a `max_sequence_index`, we apply a filter: `("sequence_index", "<=", max_sequence_index)`.

3.  **API & UX:**
    *   The API accepts an optional `max_sequence_index` parameter.
    *   **Frontend Responsibility:** The UI should allow the teacher to select the current lesson/unit. The frontend translates this selection into the corresponding `sequence_index` (or the backend provides a lookup) and sends it with the search request.
## **6\. Implementation Roadmap (4 Weeks)**

### **Week 1: The "Data Foundation"**

* [x] **Infra:** Set up Postgres (pgvector) and Redis locally via Docker Compose.
* [x] **Schema:** Run the SQL DDL for structure_nodes and content_atoms (LlamaIndex).
* [x] **Ingestion:** Implement the HybridIngestor class.

### **Week 2: The "Enrichment Engine"**

* [ ] **Vision AI:** Write script to iterate image_assets, send to Gemini Flash, and save descriptions to content_atoms (type=image_desc).
* [ ] **Curriculum Guard:** Write the SQL query template that strictly enforces WHERE sequence_index <= X.
* [x] **Embeddings:** Batch embed all text chunks using OpenAI Embedding API (via LlamaIndex).

### **Week 3: The "Scalable API"**

* [ ] **Queueing:** Implement the FastAPI + Celery pattern.
* [ ] **Caching:** Add a Redis check before calling Celery.

### **Week 4: The "Frontend & Pilot"**

* [ ] **UI:** Simple React/Streamlit app.
* [ ] **Load Test:** Simulate 50 concurrent requests.
* [ ] **Deploy:** Push to Cloud Run (API) + Neon/Supabase (DB).

## **Appendix: Future Scaling Strategy (Post-MVP)**

**Context:** The MVP uses a single `content_atoms` table with a GIN index on metadata. This works perfectly for `<10M` rows (approx. 500–1,000 textbooks).  
**Trigger:** When query latency > 200 ms or table size > 50 GB.  
**Strategy:** “Transparent Partitioning” — move from logical filtering (scanning one big index) to physical scanning (small per-book tables) without changing the application code.

### 1\. The Migration Pattern

We keep the `content_atoms` table as a “Master Interface” but use Postgres inheritance to route data.

**Step 1: Rename the old table to be the first partition**
```sql
ALTER TABLE content_atoms RENAME TO content_atoms_legacy;
```

**Step 2: Create the new parent table (partitioned)**
```sql
CREATE TABLE content_atoms (
    id UUID DEFAULT gen_random_uuid(),
    text VARCHAR,
    metadata_ JSONB,
    node_id VARCHAR,
    embedding VECTOR(1536),
    book_id VARCHAR GENERATED ALWAYS AS (metadata_->>'book_id') STORED, -- Auto-extracted column
    PRIMARY KEY (id, book_id)
) PARTITION BY LIST (book_id);
```

**Step 3: Attach partitions dynamically**
```sql
CREATE TABLE content_book_101 PARTITION OF content_atoms FOR VALUES IN ('book_uuid_101');
```

### 2\. Why This Works

* **App Logic:** The Python app still inserts into `content_atoms`.  
* **DB Logic:** Postgres automatically extracts `book_id` from the metadata JSON and routes the row to the correct physical file on disk.  
* **Performance:** Queries for `book_id='101'` only open one small file instead of scanning the terabyte-sized index.

**Summary:** We do not need to over-engineer this today. The “Metadata First” design we chose for the MVP is forward-compatible with this partitioning strategy.