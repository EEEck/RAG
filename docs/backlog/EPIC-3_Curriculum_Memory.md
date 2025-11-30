# EPIC-3: Curriculum Graph / Memory

**Status:** In Progress
**Owner:** Engineering Team
**Goal:** Track what has been taught (quizzes, lesson plans) and use it for cumulative reviews and exams.

---

## 1. Artifact Storage

### [F3-001] Artifact Data Model
**User Story:** As a developer, I want to store generated items (quizzes, lessons) as "Artifacts".
**Acceptance Criteria:**
- [x] Create `Artifact` model and DB table (`class_artifacts`).
- [x] Fields: `profile_id`, `type` (quiz, lesson), `content_blob`, `created_at`.
- [x] Support vector embeddings for `summary_text`.
**Status:** DONE

### [F3-002] Save Artifact API
**User Story:** As a teacher, I want to save a good result as an artifact for later use.
**Acceptance Criteria:**
- [x] POST `/artifacts` endpoint.
- [x] "Promote" a chat/generation response ID to an artifact.
**Status:** DONE

---

## 2. Curriculum Retrieval (Memory)

### [F3-003] Artifact Indexing
**User Story:** As a system, I want to index artifacts so I can find "what I taught last week".
**Acceptance Criteria:**
- [x] Compute embeddings for artifact summaries.
- [x] Store in `pgvector` (or separate collection).
**Status:** DONE

### [F3-004] Hybrid Search for Artifacts
**User Story:** As a system, I want to search artifacts by time ("last week") and topic ("past tense").
**Acceptance Criteria:**
- [x] Implement hybrid search (SQL filters for date/profile + Vector search for topic).
- [x] Return relevant past artifacts.
**Status:** DONE

---

## 3. Cumulative Review Generation

### [F3-005] Review Orchestration
**User Story:** As a teacher, I want to generate a review quiz based on previously taught material.
**Acceptance Criteria:**
- [ ] `retrieve_and_generate` supports "Review" mode.
- [ ] Retrieve relevant artifacts from history.
- [ ] Retrieve original textbook content for those topics.
- [ ] Combine into a review prompt.
**Status:** TODO

### [F3-006] Timeline View
**User Story:** As a teacher, I want to see a timeline of what I've taught.
**Acceptance Criteria:**
- [ ] GET `/artifacts?profile_id=X` returns ordered list.
- [ ] Filter by type (quiz, lesson).
**Status:** TODO
