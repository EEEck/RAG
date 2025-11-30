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

### [F3-005] Logic: Review Orchestration (Date & Topic Extraction)
**User Story:** As a teacher, I want to generate a review quiz based on material taught in a specific time window (e.g., "last week"), so the review is strictly relevant.
**Acceptance Criteria:**
- [ ] Implement `retrieve_and_generate` "Review Mode" or a dedicated `generate_review` service method.
- [ ] Input: `profile_id`, `date_range` (start/end) or `relative_time` ("last_7_days").
- [ ] Logic:
    1.  Fetch artifacts for the profile within the date range.
    2.  Extract key topics/concepts from these artifacts (from `topic_tags` or `summary`).
    3.  (Optional) Re-query the Textbook RAG for these specific topics to get fresh source material.
    4.  Construct a prompt: "Based on these past lessons [summaries] and this textbook content [content], generate a review quiz."
**Status:** TODO

### [F3-006] API: Artifact Filtering (Timeline View)
**User Story:** As a teacher, I want to see a timeline of what I've taught, filtered by date and type, so I can plan my next lesson.
**Acceptance Criteria:**
- [ ] Update `GET /artifacts` (or create `GET /artifacts/timeline`) to support:
    -   `start_date`, `end_date` (ISO format).
    -   `artifact_type` (e.g., `quiz`, `lesson`, `vocab`).
- [ ] Backend: Ensure SQL query handles these filters efficiently.
- [ ] Return list of lightweight Artifact objects (ID, Date, Type, Title/Summary) sorted by Date DESC.
**Status:** TODO

### [F3-007] Script: End-to-End Review Verification
**User Story:** As an engineer, I want a script that simulates a teacher's workflow (Teach -> Save -> Review) to verify the system's memory.
**Acceptance Criteria:**
- [ ] Create `docs/demo_review_workflow.py`.
- [ ] Steps to implement:
    1.  **Teach:** Generate a lesson on "Photosynthesis" (Topic A).
    2.  **Save:** Save it as an artifact with a specific timestamp (mocked if needed).
    3.  **Teach:** Generate a lesson on "Cellular Respiration" (Topic B).
    4.  **Save:** Save it.
    5.  **Review:** Call the new "Review Mode" logic for "last 7 days".
    6.  **Assert:** The generated review contains questions about *both* Photosynthesis and Respiration.
**Status:** TODO
