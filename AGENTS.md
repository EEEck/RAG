# Agents & Architecture Guidelines  
**Project: Scalable Textbook RAG (MVP)**

This document defines how AI agents and developers should design, implement, and extend the AI-for-teachers platform.

## 1. Goals & Scope

- Support **hundreds of teachers** and **hundreds of textbooks**, plus **thousands of small teacher material databases**.
- Provide a **safe, curriculum-aligned** RAG system:
  - Enforces “only taught so far” constraints (e.g., Units 1–3 only).
  - Keeps results scoped to the correct textbook / teacher collection.
- Ensure the codebase is:
  - **Domain-agnostic** (ESL, STEM, History, etc.).
  - **Testable by default** (TDD mindset).
  - **Easy to evolve** without breaking existing workflows.

Agents writing or modifying code must follow the principles and contracts in this document.

---

## 2. Core User Stories (Behavioral Contract)

These stories define what the system must support. Agents should not break these guarantees.

| Actor | Story | Acceptance Criteria |
| :---- | :---- | :------------------ |
| **Admin** | As an admin, I want to upload a PDF (e.g., "Green Line 1") and have it automatically ingested, partitioned, and indexed. | System ingests the book, builds structure nodes, and populates vector indexes with `book_id` in metadata. |
| **Teacher** | As a teacher, I want to generate a quiz for **Unit 3** that *only* uses vocabulary/grammar from Units 1–3. | Search/generation uses `sequence_index` / unit filters so no content from Unit 4+ appears. |
| **Teacher** | As a teacher, I want to select my specific textbook profile so I don’t get search results from unrelated books. | API requests are filtered by `book_id` (and possibly `teacher_collection_id`). |
| **System** | As a platform, I need to handle many teachers clicking “Generate” simultaneously without crashing. | Heavy RAG work is offloaded via a queue; users receive a `job_id` and can poll for results. |

---

## 3. Project Management & Workflow

We use a Markdown-based backlog to track progress and plan future work.

### 3.1 Backlog Structure
The backlog is located in `docs/backlog/` and consists of:

*   **`BOARD.md`**: The central project board listing all Epics and their status.
*   **`EPIC-X_Title.md`**: Detailed Epic files containing user stories, acceptance criteria, and status tracking (TODO/DONE).

### 3.2 Workflow for Agents & Developers
1.  **Check the Board:** Before starting work, review `docs/backlog/BOARD.md` to identify the active Epic.
2.  **Select a Story:** Open the relevant Epic file and find a story marked as `TODO`.
3.  **Implement:** Write code and tests to satisfy the Acceptance Criteria.
4.  **Update Status:** Once the implementation is verified, change the story status to `DONE` in the Epic file.
5.  **Reflect Changes:** If your implementation changes architectural patterns or adds new global concepts, you must update this `AGENTS.md` file to reflect the new reality.

> **Note:** Always keep the documentation in sync with the code. If `AGENTS.md` contradicts the codebase, update `AGENTS.md`.

---

## 4. High-Level Architecture

### 4.1 Stack Overview

- **Ingestion:** Python worker  
  - **Parsing:** Docling for layout + LlamaParse as a fallback for complex pages.
- **Vector Store:** LlamaIndex + `PGVectorStore` (PostgreSQL).
- **Database:** PostgreSQL 16+ with `vector` extension.
- **API Layer:** FastAPI (async).
- **Async Queue:** Redis (broker) + Celery workers for heavy RAG jobs.
- **Caching:** Redis (semantic / result cache).
- **LLM:** OpenAI / Gemini (wrapped behind an LLM client interface).

Agents must respect these layers and avoid mixing concerns (e.g., no direct DB calls from FastAPI route handlers without going through services/repositories).

---

## 5. Coding Principles & Design + TDD Mindset

All code written by humans or AI agents must follow these principles.

### 5.1 Single Responsibility & Clear Boundaries

Each module does **one job well**:

- **IngestionService (`ingest/service.py`)**
  - Orchestrates the ingestion workflow:
    - PDF → structure nodes → content atoms → vector store.
  - Knows **what** should happen in which order, but not **how** each step is implemented.
  - Delegates:
    - Parsing to injected ingestor (default `HybridIngestor`).
    - Persistence to injected repository (e.g., `StructureNodeRepository`).
    - Embedding/indexing to injected vector-store adapters.

- **Repositories** (e.g. `StructureNodeRepository`)
  - Own database persistence for a specific aggregate (structure nodes, content atoms, exam configs).
  - Do *not* contain PDF parsing logic or LLM calls.

- **SearchService**
  - Encapsulates retrieval logic.
  - Works in terms of domain objects (`ContentAtom`, `AtomHit`) and filter parameters.
  - Does not know about HTTP or UI.

- **PromptFactory**
  - Given a task + domain + context, returns the correct prompt configuration.
  - Keeps prompt templates and system messages out of business logic.

> Rule: If a class/function has more than one major reason to change (e.g. DB schema **and** LLM behavior), split it.

---

### 5.2 Dependency Injection (DI)

Core services receive dependencies via their constructors:

- Examples:
  - `IngestionService(repository, ingestor, vector_store, clock)`
  - `SearchService(vector_store, content_repository, reranker)`
  - `GradingAgent(search_service, prompt_factory, llm_client)`

Benefits:

- Easy to test (inject in-memory repos, fake vector stores, mock LLM clients).
- No tight coupling to Postgres, Redis, or specific vendors.

Constraints:

- No hidden globals / service locators.
- Wiring happens in a small, explicit bootstrap module (e.g. `app/bootstrap.py`).

---

### 5.3 Separation of Concerns & Domain-Agnostic Core

The core pipeline must be reusable across ESL, STEM, and History.

- **Domain-agnostic core**
  - Core data types: `StructureNode`, `ContentAtom`, `AtomHit`.
  - Core RAG/search logic does not know about “vocabulary vs grammar vs physics formula” in a hard-coded way.
- **Domain-specific behavior**
  - Encoded via metadata (`atom_type`, `subject`, `level`, `topic`) and simple policies.
  - ESL vs STEM is handled by filters and prompt selection, not by forking the pipeline.

- **Legacy compatibility**
  - Old helper functions (e.g. `run_ingestion(...)`) act as thin wrappers that call the new services.
  - Do not change their contract without a migration plan.

---

### 5.4 Pure Logic vs I/O (Ports & Adapters)

- **Pure logic modules**
  - Take structured data, return structured data.
  - No DB, HTTP, file system, or network calls.
  - Examples:
    - Chunking algorithms.
    - “Curriculum Guard” logic (filtering `AtomHit`s by `sequence_index`).
    - Ranking and aggregation logic.

- **Ports & adapters**
  - Ports: interfaces/protocols in the domain layer (`VectorStorePort`, `LLMClientPort`, `ContentRepositoryPort`).
  - Adapters: infra implementations (`PGVectorStore`, `OpenAIClient`, `PgContentRepository`).

Agents should:

- Depend on **ports** in core services.
- Only touch adapters in infra modules.

---

### 5.5 Composition Over Inheritance

- Prefer composing behavior over inheriting from complex base classes.
- Use small interfaces / ABCs and inject implementations instead of deep inheritance trees.

Examples:

- ✅ `GradingAgent` has a `SearchService`, `PromptFactory`, and `LLMClientPort`.
- ⚠️ Avoid generic “Manager” base classes that hide behavior and state.

---

### 5.6 TDD & Testing Strategy

We follow a **test-first / test-alongside** mindset:

> Whenever an agent or developer adds or changes behavior, they must add or update tests in the same PR.

#### 5.6.1 Types of Tests

- **Unit tests**
  - For pure logic (chunkers, curriculum guard filters, prompt constructors).
  - No DB/Redis/network. Use fakes/mocks for ports.
- **Service-level tests**
  - For `IngestionService`, `SearchService`, `GradingAgent`.
  - Use in-memory or SQLite repos and fake vector stores.
- **Integration tests**
  - For the full ingestion + search flow:
    - Example: ingest a tiny textbook → search with `max_sequence_index` → assert only correct units appear.
- **API contract tests**
  - For FastAPI routes:
    - Check status codes, response shape, and error handling.
    - Use a test DB and a test Redis or in-memory queue.

#### 5.6.2 TDD Workflow (for agents)

When implementing a new feature or refactor:

1. **Clarify behavior**  
   - Tie it to a user story and acceptance criteria (Section 2).
2. **Write or update tests first**
   - At least one failing test that captures the new behavior.
3. **Implement minimal code to pass tests**
   - Stay within existing architecture (services, repos, ports).
4. **Refactor with tests green**
   - Clean up names, split functions, improve structure.
5. **Add regression tests for bugs**
   - Every bug fixed should come with a test that would have caught it.

Agents must never introduce non-trivial logic without a corresponding test.

---

## 6. Database Schema (Universal, LlamaIndex-Compatible)

We use a universal schema that separates **structure** from **content atoms**.

### 6.1 Structure Nodes

Hierarchy: `Book → Unit → Section/Lesson → (optional) Subsection`.

For the authoritative SQL schema, please refer to `ingest/infra/postgres.py`.

```sql
-- See ingest/infra/postgres.py for the full DDL
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE structure_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL,
    parent_id UUID REFERENCES structure_nodes(id),
    node_level INTEGER, -- 0=Book, 1=Unit, 2=Section/Lesson
    title TEXT,
    sequence_index INTEGER, -- Strict order for curriculum safety (1 < 2 < 3...)
    meta_data JSONB -- {"page_start": 10, "page_end": 12}
);
```

### 6.2 Content Atoms (LlamaIndex-Managed)

- LlamaIndex manages the vector table (typically named `data_content_atoms` by `PGVectorStore`):
  - Columns: `id`, `text`, `metadata_` (JSONB), `embedding`.
  - Important metadata fields:
    - `book_id`
    - `node_id`
    - `atom_type` (e.g., `text`, `vocab`, `exercise`, `image_desc`)
    - `sequence_index`

Agents must ensure:

- `sequence_index` and `book_id` are always set correctly during ingestion.
- Metadata contains enough information for domain-specific filtering (e.g., `unit`, `lesson`, `subject`).

---

## 7. Ingestion Architecture

1. **IngestionService**
   - Entry point for ingestion requests.
   - Orchestrates:
     1. Parse with injected Ingestor strategy (default `HybridIngestor`: Docling + LlamaParse fallback).
     2. Build `StructureNode` tree.
     3. Create `ContentAtom` records with proper metadata (`book_id`, `node_id`, `sequence_index`).
     4. Persist structure via `StructureNodeRepository`.
     5. Push atoms to the vector store via LlamaIndex.

2. **HybridIngestor**
   - Strategy that combines:
     - Docling (layout-aware).
     - LlamaParse (complex tables/regions).
   - Returns structured representations that IngestionService converts into nodes/atoms.

3. **Async Enrichment (Optional)**
   - Post-ingestion tasks (e.g., vision descriptions for images) are triggered as Celery jobs.
   - Output (e.g., `image_desc` atoms) is written as additional `ContentAtom` rows.

---

## 8. Search & Generation Architecture

### 8.1 Generic Retrieval (SearchService)

- `SearchService.search_content(...)`:
  - Returns a list of `AtomHit` objects.
  - Applies filters:
    - `book_id`
    - `sequence_index` <= `max_sequence_index`
    - optional domain filters (`subject`, `atom_type`, etc.)
  - Uses LlamaIndex’s metadata filters and vector search.

- The service is **agnostic** to:
  - Whether content is ESL, STEM, or History.
  - Whether the atom is text, vocabulary, or image description.

### 8.2 Dynamic Generation (PromptFactory + LLM Client)

- **PromptFactory**
  - Input: `GenerateItemsRequest` with fields like:
    - `category` (`language`, `stem`, `history`)
    - `task_type` (`quiz`, `cloze`, `translation`, etc.)
    - `level`, `language`, etc.
  - Output: a typed prompt object containing system + user messages.

- **Grading / Quiz Agents**
  - Use `SearchService` to fetch `AtomHit`s.
  - Inject `AtomHit` content into the prompt as “Source Material”.
  - Call the LLM through `LLMClientPort`.
  - Return structured results (e.g., `QuizItem[]`, `GradingResult`) — not raw strings if possible.

---

## 9. API & Scaling Architecture

To handle bursts (e.g., many teachers clicking “Generate”):

- **FastAPI**:
  - Receives requests and validates input.
  - Enqueues heavy RAG work via Celery.
  - Returns a `job_id` immediately.

- **Redis (Broker & Cache)**:
  - Stores Celery tasks and job statuses.
  - Can cache frequent results (e.g., “Unit 3 vocab quiz for Book X”).

- **Celery Workers**:
  - Execute ingestion, search+generate, and enrichment jobs.
  - Use services (`IngestionService`, `SearchService`, `GradingAgent`) with injected dependencies.

- **Frontend**:
  - Polls `/job/{id}` every N seconds or uses server-sent events/WebSockets in future.

Agents must not:

- Block FastAPI request handlers with slow LLM calls or long-running ingestion.
- Bypass the queue for heavy jobs.

---

## 10. Curriculum Guard (Sequence Index Filtering)

### 10.1 Idea

Teachers should only get content up to what has been taught so far.

- We enforce this via `sequence_index`:
  - Each `StructureNode` has a `sequence_index`.
  - This value is denormalized into `ContentAtom.metadata.sequence_index`.

### 10.2 Implementation

1. **Ingestion**
   - When IngestionService creates `ContentAtom`s, it:
     - Reads `sequence_index` from the corresponding `StructureNode`.
     - Stores it into the atom’s metadata (`"sequence_index": <int>`).
2. **Search (LlamaIndex)**
   - When a request includes `max_sequence_index`, SearchService:
     - Adds a LlamaIndex metadata filter: `("sequence_index", "<=", max_sequence_index)`.
3. **API & UX**
   - The API accepts a `max_sequence_index` or a higher-level “current unit/lesson”.
   - The frontend:
     - Lets the teacher choose current unit/lesson.
     - Maps that to a `sequence_index` and sends it to the backend (or calls a backend endpoint to resolve it).

Agents must **always** respect `max_sequence_index` when generating quizzes or exercises that claim to be “curriculum safe”.

---

## 11. Future Scaling Strategy (Post-MVP Partitioning)

The MVP uses a single `content_atoms` table, which works well up to ~10M rows / ~500–1,000 textbooks.

When latency grows too high or table size becomes large, we can move to partitioning without changing application code.

### 11.1 Partitioning Pattern (Conceptual)

- Keep `content_atoms` as the logical interface.
- Use Postgres partitioning by `book_id`:
  - A parent `content_atoms` table, partitioned by `book_id`.
  - Child tables like `content_atoms_book_<id>` for each large book.

Example DDL (illustrative):

```sql
CREATE TABLE content_atoms (
    id UUID DEFAULT gen_random_uuid(),
    text VARCHAR,
    metadata_ JSONB,
    node_id VARCHAR,
    embedding VECTOR(1536),
    book_id VARCHAR GENERATED ALWAYS AS (metadata_->>'book_id') STORED,
    PRIMARY KEY (id, book_id)
) PARTITION BY LIST (book_id);

CREATE TABLE content_book_101
PARTITION OF content_atoms
FOR VALUES IN ('book_uuid_101');
```

- The Python app continues to write to `content_atoms`.
- Postgres automatically routes rows to the correct partition based on `book_id`.

Agents must not depend on physical table names; always use the logical `content_atoms` abstraction.

---

## 12. Style & Readability Guidelines

- Prefer **descriptive names**:  
  `extract_vocab_items_from_page` > `process_page`.
- Small, focused functions over large multi-purpose ones.
- Comments explain **why**, not just what:
  - Document non-obvious decisions, tradeoffs, and assumptions.
- Follow project linting/formatting (e.g., `black`, `ruff`, `mypy` if enabled).
- New code should align with the existing folder structure and patterns.

---

**Summary:**  
This `agents.md` is the contract. Any new service, endpoint, or agent behavior should:

1. Map back to the user stories in Section 2.
2. Respect the architecture and boundaries in Sections 4–11.
3. Be implemented with TDD and DI in mind (Section 5).
4. Keep options open for the future partitioning strategy (Section 11).
