# Project Backlog & Status Board

This board tracks the high-level progress of the AI Teaching Assistant Platform MVP.

## Epics Overview

| ID | Epic Name | Status | Description |
| :--- | :--- | :--- | :--- |
| **[EPIC-1](EPIC-1_Textbook_RAG.md)** | **Textbook RAG Engine** | 🟡 **In Progress** | Core ingestion, vector search. **Focus:** Discovery API & Search Safety. |
| **[EPIC-2](EPIC-2_Classroom_Profiles.md)** | **Classroom Profiles** | 🟢 **Done** | Persist teacher settings, pedagogy, and active textbook links. |
| **[EPIC-3](EPIC-3_Curriculum_Memory.md)** | **Curriculum Memory** | 🟡 **In Progress** | Save generated artifacts. **Focus:** Review Logic & Timeline Filters. |
| **[EPIC-4](EPIC-4_Infrastructure.md)** | **Infrastructure & Hosting** | 🟡 **In Progress** | Split DB architecture (Content vs User), Docker improvements, and GCP planning. |
| **[EPIC-5](EPIC-5_User_Content.md)** | **User Content Library** | 🟡 **In Progress** | Allow teachers to upload private content. **Focus:** Schema migration & Privacy. |

## Workflow

1.  **Pick an Epic:** Start with the highest priority Epic.
2.  **Select a Story:** Identify a `TODO` story within the Epic.
3.  **Implement & Test:** Follow TDD (write test -> implement -> refactor).
4.  **Mark Done:** Update the Epic file to mark the story as `[x] ... Status: DONE`.
5.  **Reflect:** Update `AGENTS.md` if new architectural patterns emerge.

## Current Focus
*   **User Content:** Implement [USER-001] Schema Migration and [USER-002] Ingestion Updates.
*   **Infrastructure:** Implement Split-DB architecture ([EPIC-4]).
*   **Discovery & Safety:** Implement [F1-010] List Books API and [F1-011] Search Scoping.
*   **Memory Intelligence:** Implement [F3-005] Review Logic and [F3-006] Timeline Filters.
