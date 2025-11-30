# EPIC-2: Classroom Context / Profile Engine

**Status:** Backlog
**Owner:** Engineering Team
**Goal:** Persist classroom context (grade, book, pedagogy) and inject it automatically into every generation.

---

## 1. Profile Management

### [F2-001] Profile Data Model
**User Story:** As a developer, I want a database schema for Teacher Profiles so I can store preferences.
**Acceptance Criteria:**
- [ ] Create `TeacherProfile` Pydantic model and DB table.
- [ ] Fields: `user_id`, `name`, `grade_level`.
- [ ] Sub-models: `PedagogyConfig`, `ContentScope`.
**Status:** TODO

### [F2-002] Profile CRUD API
**User Story:** As a teacher, I want to create and update class profiles (e.g., "Tuesday Grammar Class").
**Acceptance Criteria:**
- [ ] POST `/profiles` to create a profile.
- [ ] GET `/profiles` to list profiles.
- [ ] PUT `/profiles/{id}` to update settings.
**Status:** TODO

### [F2-003] Textbook Linking
**User Story:** As a teacher, I want to link a specific textbook to my profile so I don't have to select it every time.
**Acceptance Criteria:**
- [ ] Profile contains `primary_textbook_id`.
- [ ] UI/API flow to search books and attach to profile.
**Status:** TODO

---

## 2. Context Injection

### [F2-004] Context Orchestrator
**User Story:** As a system, I want to fetch the active profile's settings during generation to customize the output.
**Acceptance Criteria:**
- [ ] Modify `retrieve_and_generate` to accept `profile_id`.
- [ ] Fetch `PedagogyConfig` (tone, style) from DB.
- [ ] Inject pedagogy instructions into the system prompt.
**Status:** TODO

### [F2-005] Dynamic Prompting based on Pedagogy
**User Story:** As a teacher, I want the AI to use specific strategies (e.g., "TPR", "Gamified") defined in my profile.
**Acceptance Criteria:**
- [ ] `PromptFactory` uses `PedagogyConfig` to select/modify templates.
- [ ] Support strategies like: strict grammar, conversation focus, etc.
**Status:** TODO

---

## 3. UI & Usage

### [F2-006] Profile Switcher
**User Story:** As a teacher, I want to easily switch between profiles (e.g., Grade 2 Math -> Grade 8 Physics).
**Acceptance Criteria:**
- [ ] API endpoint to "activate" a session profile (or pass it in every request).
**Status:** TODO
