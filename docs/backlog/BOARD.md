# Project Backlog & Status Board

This board tracks the high-level progress of the AI Teaching Assistant Platform MVP.

## Epics Overview

| ID | Epic Name | Status | Description |
| :--- | :--- | :--- | :--- |
| **[EPIC-1](EPIC-1_Textbook_RAG.md)** | **Textbook RAG Engine** | 🟢 **Done/Stable** | Core ingestion, vector search, and curriculum-safe retrieval. |
| **[EPIC-2](EPIC-2_Classroom_Profiles.md)** | **Classroom Profiles** | 🔴 **Todo** | Persist teacher settings, pedagogy, and active textbook links. |
| **[EPIC-3](EPIC-3_Curriculum_Memory.md)** | **Curriculum Memory** | 🔴 **Todo** | Save generated artifacts and enable cumulative reviews over time. |

## Workflow

1.  **Pick an Epic:** Start with the highest priority Epic (currently working towards Feature 2).
2.  **Select a Story:** Identify a `TODO` story within the Epic.
3.  **Implement & Test:** Follow TDD (write test -> implement -> refactor).
4.  **Mark Done:** Update the Epic file to mark the story as `[x] ... Status: DONE`.
5.  **Reflect:** Update `AGENTS.md` if new architectural patterns emerge.

## Current Focus
*   Maintain stability of **EPIC-1**.
*   Begin planning and implementation of **EPIC-2**.
