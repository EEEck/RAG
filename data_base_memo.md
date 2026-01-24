# Database Memo: User Content Strategy

**Date:** 2024-05-23
**Status:** Draft
**Scope:** MVP Feature - Teacher-Uploaded Content (Textbooks/Manuscripts)

---

## 1. Architecture Decision: Unified Content DB

We have decided to adopt a **Unified Content Database** approach ("Option A") for managing user-uploaded content alongside global static textbooks.

### The Decision
Instead of creating parallel tables in `db_user` for user content (which would require complex "federated" search logic across multiple vector stores), we will extend the existing `db_content` schema to support ownership.

This mirrors the pattern already established in the `pedagogy_strategies` table, which uses an `owner_id` column to distinguish between Global strategies (`owner_id` IS NULL) and User-specific strategies (`owner_id` = 'user_123').

### Rationale
*   **Simpler Search Logic:** The `SearchService` continues to query a single Vector Index (`content_atoms`). We simply append a metadata filter (`owner_id IN [NULL, current_user_id]`) to every query.
*   **Reuse of Pipeline:** The existing `StructureNode` hierarchy (Book -> Unit -> Section) is robust. Reusing it for user uploads avoids maintaining two separate ingestion codebases.
*   **Performance:** Postgres RLS (Row Level Security) or simple application-level filtering on a single table is generally more performant and easier to index than joining results from two distinct databases.

---

## 2. Database Schema Changes

We will modify the `db_content` schema (defined in `ingest/infra/postgres.py`) to introduce ownership concepts.

### 2.1 Table: `structure_nodes`
We need to track who "owns" a book structure.

```sql
ALTER TABLE structure_nodes
ADD COLUMN owner_id TEXT DEFAULT NULL; -- NULL = Global, TEXT = user_id

-- Create index for faster filtering
CREATE INDEX idx_structure_nodes_owner ON structure_nodes(owner_id);
```

### 2.2 Vector Store: `content_atoms`
The `data_content_atoms` table is managed by LlamaIndex, but we control the metadata injected into it.

*   **Action:** Update `IngestionService` to inject `owner_id` into the metadata dictionary of every `ContentAtom` before indexing.
*   **Result:** LlamaIndex will store `owner_id` in the JSONB `metadata_` column.
*   **Querying:** We will add a metadata filter to `SearchService` to restrict results.

---

## 3. MVP Scope & Ingestion

The goal is to allow teachers to upload private manuscripts or textbooks they have rights to use, which we cannot provide globally due to copyright.

### 3.1 Ingestion Interface
*   **Initial MVP:** "Admin-Assisted" scripts or a simple API Endpoint.
    *   We will expose a new endpoint `POST /ingest` (admin-only or authenticated) that accepts a file and a `user_id`.
    *   This endpoint will trigger the existing `IngestionService`.
*   **Future:** A full UI "Upload Wizard".

### 3.2 Simplified Hierarchy
While our system supports deep "Book -> Unit -> Section" hierarchies, user uploads (often flat PDFs) might not map perfectly.
*   **Strategy:** We will rely on the existing `HybridIngestor` auto-detection.
*   **Fallback:** If structure cannot be detected, we default to a simple 2-level structure: `Book (Root) -> "Content" (Node)`.

---

## 4. Privacy & Search Logic

Privacy is paramount. User content must **never** leak to other users.

### Search Service Updates
The `SearchService` (in `app/services/search_service.py`) currently filters by `book_id` and `curriculum_guards`. It must be updated to be "User-Aware".

**New Logic:**
1.  **Input:** `search_content(query, user_id, ...)`
2.  **Filter Construction:**
    ```python
    # Pseudo-code
    filters = [
        # ... existing filters (book_ids, unit) ...
        OR(
            MetadataFilter(key="owner_id", value=None, operator=EQ),       # Global
            MetadataFilter(key="owner_id", value=user_id, operator=EQ)     # Private
        )
    ]
    ```
3.  **Strict Mode:** If a user searches within a specific `book_id`, we must first verify they have access to that book (i.e., it is either Global or Owned by them).

### Timeline
1.  **Schema Migration:** Add `owner_id` column.
2.  **Ingestor Update:** Pass `owner_id` through `StructureNode` and `ContentAtom`.
3.  **Search Update:** Enforce `owner_id` filtering in `SearchService`.
4.  **API:** Create `POST /ingest` endpoint.
