# EPIC-4: Infrastructure & Hosting (Split Architecture)

**Status:** 🟡 In Progress
**Owner:** DevOps / Lead Engineer

## Goal
Transition the platform from a monolithic "single DB" MVP setup to a scalable, split-database architecture that separates **Static Content** (Textbooks, Global Pedagogy) from **User Data** (Profiles, Artifacts). This prepares the system for cloud hosting (GCP) and cleaner multi-tenancy.

## User Stories

| ID | Story | Status |
| :--- | :--- | :--- |
| **I4-001** | **Infrastructure Plan** <br> Create a detailed architecture doc for the split-DB hosting strategy. | TODO |
| **I4-002** | **Docker Split** <br> Update `docker-compose.yml` to run `db_content` and `db_user` services. | TODO |
| **I4-003** | **App Config Refactor** <br> Update app to handle multiple DB connections (`CONTENT_DB`, `USER_DB`). | TODO |
| **I4-004** | **Schema Migration** <br> Split SQL DDLs and ensure correct tables are created in the correct DB. | TODO |
| **I4-005** | **User Pedagogy Support** <br> Add `owner_id` to `pedagogy_strategies` to allow user-specific overrides in the global DB. | TODO |

## Acceptance Criteria
- `docker-compose up` spins up 2 Postgres instances.
- Ingestion pipeline writes only to `db_content`.
- Profile/Artifact services write only to `db_user`.
- Tests pass (mocking the split correctly).
