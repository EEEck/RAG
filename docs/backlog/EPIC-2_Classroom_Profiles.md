# EPIC-2: Classroom Context / Profile Engine

**Status:** Done
**Owner:** Engineering Team
**Goal:** Persist classroom context (grade, book, pedagogy) and inject it automatically into every generation.

---

## 1. Profile Management

### [F2-001] Profile Data Model
**User Story:** As a developer, I want a database schema for Teacher Profiles so I can store preferences.
**Acceptance Criteria:**
- [x] Create `TeacherProfile` Pydantic model and DB table.
- [x] Fields: `user_id`, `name`, `grade_level`.
- [x] Sub-models: `PedagogyConfig`, `ContentScope`.
**Status:** DONE

### [F2-002] Profile CRUD API
**User Story:** As a teacher, I want to create and update class profiles (e.g., "Tuesday Grammar Class").
**Acceptance Criteria:**
- [x] POST `/profiles` to create a profile.
- [x] GET `/profiles` to list profiles.
- [x] PUT `/profiles/{id}` to update settings.
**Status:** DONE

### [F2-003] Textbook Linking
**User Story:** As a teacher, I want to link a specific textbook to my profile so I don't have to select it every time.
**Acceptance Criteria:**
- [x] Profile contains `primary_textbook_id`.
- [x] UI/API flow to search books and attach to profile.
**Status:** DONE

---

## 2. Context Injection

### [F2-004] Context Orchestrator
**User Story:** As a system, I want to fetch the active profile's settings during generation to customize the output.
**Acceptance Criteria:**
- [x] Modify `retrieve_and_generate` to accept `profile_id`.
- [x] Fetch `PedagogyConfig` (tone, style) from DB.
- [x] Inject pedagogy instructions into the system prompt.
**Status:** DONE

### [F2-005] Dynamic Prompting based on Pedagogy
**User Story:** As a teacher, I want the AI to use specific strategies (e.g., "TPR", "Gamified") defined in my profile.
**Acceptance Criteria:**
- [x] `PromptFactory` uses `PedagogyConfig` to select/modify templates.
- [x] Support strategies like: strict grammar, conversation focus, etc.
**Status:** DONE

---

## 3. Pedagogy Intelligence (New)

### [F2-007] Pedagogy Strategy Database
**User Story:** As a system, I need a database to store pedagogical guides (e.g., "Lehrplan", "Teaching Methods") distinct from textbooks.
**Acceptance Criteria:**
- [ ] Create `pedagogy_strategies` table with fields: `subject`, `min_grade`, `max_grade`, `institution_type`, `prompt_injection`, `embedding`.
- [ ] Add `PedagogyStrategy` Pydantic model.
**Status:** TODO

### [F2-008] Pedagogy Ingestion
**User Story:** As an admin, I want to ingest PDF teaching guides so they can be searched.
**Acceptance Criteria:**
- [ ] Implement `ingest_pedagogy_guide` to parse PDF.
- [ ] Extract metadata (Grade, Subject) via LLM.
- [ ] Embed summary and save to DB.
**Status:** TODO

### [F2-009] Pedagogy Search & Prompt Synthesis
**User Story:** As a teacher, I want the system to suggest a teaching style based on my class context (Grade 5 English).
**Acceptance Criteria:**
- [ ] Implement search by metadata + vector similarity.
- [ ] Implement `generate_system_prompt` to synthesize multiple strategies into one prompt.
**Status:** TODO

### [F2-010] Profile Wizard Notebook
**User Story:** As a developer/user, I want an interactive notebook to demo the "Profile Setup" flow.
**Acceptance Criteria:**
- [ ] Notebook: Ingest Guide -> Search Context -> Refine Prompt -> Save Profile.
**Status:** TODO

---

## 4. UI & Usage

### [F2-006] Profile Switcher
**User Story:** As a teacher, I want to easily switch between profiles (e.g., Grade 2 Math -> Grade 8 Physics).
**Acceptance Criteria:**
- [x] API endpoint to "activate" a session profile (or pass it in every request).
**Status:** DONE
