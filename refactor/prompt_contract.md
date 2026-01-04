# TeacherCopilot — Prompt Contract (v1)

This document defines the **required inputs**, **bucket formatting**, **system constraints**, and **output template** for lesson generation.

---

## 1) Teacher input schema (minimum)

**Required**
- `book_id` (e.g., ESL_Vol3)
- `year` (integer)
- `chapter` (integer)
- `topic` (string)

**Optional (defaultable)**
- `lesson_minutes`: 45 (default)
- `intent`: `introduce` | `review` | `practice` | `exam_prep` (default: introduce)
- `recap_dial`: `default` (default = prior years + earlier chapters this year)
- `output_mode`: `lecture_only` | `lecture_plus_checks` (default: lecture_plus_checks)

---

## 2) Retrieval contract (what the backend must produce)

The backend must return the following **three buckets** for every generation call:

### Bucket A — GLOBAL BACKGROUND (knowledge_items)
- One “to-date” rollup per applicable type (subject-dependent), e.g.:
  - ESL: `vocab_to_date`, `rules_to_date`
  - STEM: `definitions_to_date`, `formulas_to_date`, `procedures_to_date`
- Optional: top-k topic-relevant knowledge_items (still gated by introduced_at <= current boundary)
- Book/year overview items if available

### Bucket B — PRIOR RECAP (dial-controlled summaries)
- List of `chapter_summary` items for the allowed scope (compact)

### Bucket C — TARGET CORE CONTENT (parents)
- Ordered parents for the target chapter
- Optional: topic-selected parents (atoms→parents), deduped and inserted in textbook order

Each node/item must include **breadcrumbs** for citations:
- `Book | Year | Chapter | Page | Section`

---

## 3) System constraints (must be in system prompt)

- Use **ONLY** the provided context buckets.
- If something is not in context, say: **“Not in the provided textbook content.”**
- Do not add external facts, examples, or definitions.
- Maintain sequential safety: do not use terms beyond allowed scope.
- Every paragraph must include breadcrumbs: `(Book | Year | Chapter | Page | Section)`.

---

## 4) Prompt formatting (recommended)

### 4.1 System prompt (template)

You are TeacherCopilot, a pedagogical expert.

RULES:
1) Use ONLY the content in the provided buckets.
2) Do not introduce external facts or examples.
3) Every paragraph must end with a citation in the form: (Book | Year | Chapter | Page | Section).
4) If required info is missing, write: "Not in the provided textbook content."

OUTPUT:
- Strict Markdown.
- Follow the template in section 5.

### 4.2 User prompt (template)

LESSON REQUEST:
- Book: {book_id}
- Year: {year}
- Chapter: {chapter}
- Topic: {topic}
- Minutes: {lesson_minutes}
- Intent: {intent}
- Recap dial: {recap_dial}

BUCKET A — GLOBAL BACKGROUND (knowledge_items)
{global_background_md}

BUCKET B — PRIOR RECAP (summaries)
{prior_recap_md}

BUCKET C — TARGET CORE CONTENT (parents)
{target_core_content_md}

---

## 5) Output template (Markdown)

# {Lesson Title}

## Learning Objectives
- ...

## Quick Recap (Prerequisite Knowledge)
- ...

## Main Lesson (Target Content)
### 1) ...
- ...

### 2) ...
- ...

## Worked Examples / Practice (if present in textbook)
- ...

## Quick Checks (optional)
1. ...
2. ...

## Vocabulary / Key Terms (subject-specific)
- ...

---

## 6) Validators (backend checks)

### 6.1 Required validators (P0/P1)
- **Citation coverage:** every paragraph includes breadcrumbs.
- **Sequential safety:** detect future chapter/year references (based on metadata tags, allowlists, and/or future-only lexicons).
- **Markdown sanity:** headings/lists present; no broken tables.

### 6.2 ESL-only validator (optional P1)
- **Vocab gate:** ensure tokens are within `vocab_to_date + target_chapter_vocab` (+ small whitelist for proper nouns).

---

## 7) Recap dial semantics

- `default`: include prior years + earlier chapters this year (summaries + to-date rollups).
- `minimal`: include only short to-date rollups; no detailed summaries.
- `full`: include chapter summaries for all prior scope + any linked chapter resources (vocab/grammar/concept overviews).

---

## 8) Notes on “to-date” rollups

To-date rollups should be generated at ingestion boundaries (year/chapter).  
Runtime then becomes a simple SQL fetch:
- `SELECT ... WHERE item_type IN (...) AND introduced_at <= boundary ORDER BY introduced_at DESC LIMIT 1;`
