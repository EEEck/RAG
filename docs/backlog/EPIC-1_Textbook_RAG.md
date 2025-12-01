# EPIC-1: Scalable Textbook RAG Engine

**Status:** Done
**Owner:** Engineering Team
**Goal:** Ingest ESL/Science textbooks, enforce curriculum safety (e.g., “up to Unit 3 only”), and generate quizzes/lessons.

---

## 1. Ingestion Pipeline

### [F1-001] Core Ingestion Service
**User Story:** As an admin, I want to ingest a textbook PDF so that it is parsed into structure nodes and content atoms.
**Acceptance Criteria:**
- [x] `IngestionService` orchestrates parsing, persistence, and indexing.
- [x] `HybridIngestor` parses PDFs using Docling (with LlamaParse fallback).
- [x] `StructureNode` hierarchy is created (Book -> Unit -> Section).
- [x] `ContentAtom`s are created with `book_id` and `sequence_index`.
**Status:** DONE

### [F1-002] Vector Persistence & Indexing
**User Story:** As a system, I want to store content atoms in a vector database so they can be semantically searched.
**Acceptance Criteria:**
- [x] `PGVectorStore` is configured.
- [x] Atoms are stored in `content_atoms` table.
- [x] Metadata includes `book_id`, `node_id`, `sequence_index`, `atom_type`.
**Status:** DONE

### [F1-003] Curriculum Guard (Sequence Indexing)
**User Story:** As a system, I want to tag every atom with a sequence index so I can filter out future content.
**Acceptance Criteria:**
- [x] `StructureNode`s have a `sequence_index`.
- [x] Ingestion propagates `sequence_index` to `ContentAtom` metadata.
- [x] Vector store supports filtering by `sequence_index`.
**Status:** DONE

### [F1-004] Async Vision Enrichment
**User Story:** As a system, I want to asynchronously generate descriptions for images in the textbook so they are searchable.
**Acceptance Criteria:**
- [x] Celery task `enrich_images_task` exists.
- [x] `VisionEnricher` processes images using GPT-4o.
- [x] Descriptions are saved back as content atoms.
**Status:** DONE

---

## 2. Retrieval & Generation

### [F1-005] Search Service with Filters
**User Story:** As a teacher, I want to search for content within a specific book and unit range.
**Acceptance Criteria:**
- [x] `SearchService` accepts `book_id` and `max_sequence_index`.
- [x] LlamaIndex `MetadataFilters` are applied correctly.
- [x] Returns generic `AtomHit` objects.
**Status:** DONE

### [F1-006] RAG Orchestration
**User Story:** As a teacher, I want to generate a quiz where the LLM uses only retrieved textbook content.
**Acceptance Criteria:**
- [x] `retrieve_and_generate` function orchestrates search and generation.
- [x] Retrieved context is injected into the LLM prompt.
- [x] System prompts adapt to category (Language vs. STEM).
**Status:** DONE

### [F1-007] Async Generation API
**User Story:** As a teacher, I want to request a generation job and poll for results so the system doesn't time out.
**Acceptance Criteria:**
- [x] POST `/generate/quiz` enqueues a Celery task.
- [x] GET `/jobs/{job_id}` returns status and result.
- [x] Redis is used as the broker/backend.
**Status:** DONE

---

## 3. Testing & Verification

### [F1-008] Integration Testing
**User Story:** As an engineer, I want to verify the pipeline end-to-end with a test PDF.
**Acceptance Criteria:**
- [x] Tests exist for `IngestionService`.
- [x] Tests exist for `SearchService` filters.
- [x] `tests/integration/test_pipeline_local.py` validates the flow.
**Status:** DONE

### [F1-009] CLI Tools for Ingestion
**User Story:** As an admin, I want scripts to run ingestion manually.
**Acceptance Criteria:**
- [x] Scripts or entry points available to trigger ingestion (via code or potential CLI wrappers).
**Status:** DONE

---

## 4. API & Discovery Enhancements

### [F1-010] API: List Available Textbooks
**User Story:** As a teacher, I want to see a list of available textbooks so I can link the correct book to my class profile.
**Acceptance Criteria:**
- [x] Implement `GET /books` endpoint.
- [x] Return list of books (ID, Title, Subject, Grade Level) derived from `structure_nodes` (level=0).
- [x] Allow optional filtering by subject or grade.
- [x] Unit test: Verify endpoint returns unique books from DB.
**Status:** DONE

### [F1-011] API: Strict Profile-Based Search Scoping
**User Story:** As a platform owner, I want to enforce that all searches are strictly scoped to a profile's assigned textbook to prevent data leakage.
**Acceptance Criteria:**
- [x] Update `SearchRequest` schema to include optional `book_id` and `profile_id`.
- [x] Update `SearchService` (or Route handler) to:
    - If `profile_id` is provided, fetch the linked `book_id`.
    - If `book_id` is provided, use it.
    - If neither is provided, **Reject** the request (or require a strict "admin_override" flag).
- [x] Ensure `strict_mode` prevents queries across "all books".
**Status:** DONE
