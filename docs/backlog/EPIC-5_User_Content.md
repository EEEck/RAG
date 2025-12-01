# EPIC-5: User Content Library

**Status:** 🟡 **In Progress**

## Overview
Enable teachers to upload private content (manuscripts, scanned textbooks, PDFs) that is indexed alongside global content but remains strictly private to the uploader. This utilizes a "Unified Content DB" architecture where user content lives in `db_content` but is secured via an `owner_id` column.

## Goals
- Allow users to upload PDF documents.
- Index these documents into the RAG engine with a simplified structure.
- Ensure strict privacy: User A cannot see User B's content.
- Integrate user content seamlessly into the search experience.

## User Stories

### [USER-001] Database Schema Migration
**Status:** 🔴 **TODO**
**Priority:** High
**Description:**
Update the `db_content` schema to support ownership tracking on structure nodes.
- **Task:** Alter `structure_nodes` table to add `owner_id` (TEXT, Nullable).
- **Task:** Create an index on `owner_id` for performance.
- **Acceptance Criteria:**
  - `structure_nodes` table has an `owner_id` column.
  - Existing global content has `owner_id = NULL`.
  - Database migration script (or update to `ingest/infra/postgres.py`) is verified.

### [USER-002] Ingestion Service Updates
**Status:** 🔴 **TODO**
**Priority:** High
**Description:**
Update the ingestion logic to propagate ownership information from the entry point down to the vector store.
- **Task:** Update `IngestionService.ingest_book` to accept an optional `owner_id`.
- **Task:** Inject `owner_id` into `StructureNode` objects during persistence.
- **Task:** Inject `owner_id` into `ContentAtom` metadata before indexing to LlamaIndex (`metadata_` JSONB column).
- **Acceptance Criteria:**
  - Calling ingest with an owner ID results in vectors with `metadata.owner_id` set.
  - `structure_nodes` rows have the correct `owner_id`.

### [USER-003] Search Service Privacy Enforcement
**Status:** 🔴 **TODO**
**Priority:** Critical
**Description:**
Ensure that search results never leak private content to unauthorized users.
- **Task:** Update `SearchService.search_content` to accept a `user_id`.
- **Task:** Implement a mandatory filter: `owner_id IN (NULL, user_id)`.
- **Task:** If `strict_mode` or specific `book_ids` are requested, verify the user has access to those books before searching.
- **Acceptance Criteria:**
  - Search as User A does NOT return User B's content.
  - Search as User A DOES return Global content + User A's content.

### [USER-004] User Ingestion API
**Status:** 🔴 **TODO**
**Priority:** Medium
**Description:**
Expose a simple API endpoint for uploading content, intended for admin-assisted or self-serve use.
- **Task:** Create `POST /ingest` endpoint.
- **Task:** Accept file upload and `user_id` (from auth context or param for MVP).
- **Task:** Trigger `IngestionService` with the uploaded file.
- **Acceptance Criteria:**
  - `curl -X POST /ingest -F "file=@my_book.pdf"` successfully triggers ingestion.
  - The resulting book is linked to the user.
