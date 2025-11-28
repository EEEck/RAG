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
