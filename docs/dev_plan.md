# Development Plan & Architectural Decisions

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
