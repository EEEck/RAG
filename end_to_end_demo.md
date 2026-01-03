# End-to-End Demo Plan (Local, Docker Compose)

## Goals
- Bring up the backend + split Postgres DBs + Redis with `docker-compose up`.
- Ingest a Docling Markdown/JSON export into the content DB.
- Seed pedagogy/teaching rules from a file in `data/`.
- Run a retrieval + generation flow (API or notebook) and verify results.

## Prereqs
- Docker + Docker Compose installed.
- `.env` contains at least `OPENAI_API_KEY` (embeddings + generation).
- Data files available:
  - Textbook: `data/toy_green_line_1.md` or `data/toy_green_line_1_docling.json`
  - Teaching rules/guide: `data/ESL_1st_guide_german.pdf` (or a JSON/MD seed file if you prefer)

## Step 1: Boot infrastructure
```bash
docker-compose up --build -d
```

Verify:
```bash
curl http://localhost:8000/health
```

## Step 2: Initialize schemas + indexes
- Content DB schema is ensured at app startup and on ingestion.
- User DB schema is ensured at app startup.
- Create the GIN index on the vector table metadata (optional but recommended):
```bash
python add_gin_index.py
```

## Step 3: Seed pedagogy/teaching rules
Run the seed helper to insert a pedagogy strategy into `db_content.pedagogy_strategies`:
```bash
python -m ingest.pedagogy_seed --file data/ESL_1st_guide_german.pdf --max-pages 3
```

If you want to use JSON instead, create `data/pedagogy_strategies.json` and run:
```bash
python -m ingest.pedagogy_seed --file data/pedagogy_strategies.json
```

## Step 4: Ingest the textbook into the content DB
Choose one input format:

Docling JSON:
```bash
python -m ingest.pipeline --file data/toy_green_line_1_docling.json --book-id 12345678-1234-5678-1234-567812345678 --category language
```

Docling Markdown:
```bash
python -m ingest.pipeline --file data/toy_green_line_1.md --book-id 12345678-1234-5678-1234-567812345678 --category language
```

If you do not have an OpenAI key and want to skip embeddings:
```bash
python -m ingest.pipeline --file data/toy_green_line_1.md --book-id 12345678-1234-5678-1234-567812345678 --category language --mock-embeddings
```

## Step 5: Run a RAG query
Option A: Use the Investor demo notebook
1. Start Jupyter locally.
2. Open `notebooks/investor_demo.ipynb`.
3. Run cells in order (it creates a profile, ingests, then queries).

Option B: Use the API
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Where are you from?\",\"book_id\":\"12345678-1234-5678-1234-567812345678\",\"max_unit\":1}"
```

## Step 6: Verify data landed
- Content DB tables: `structure_nodes`, `pedagogy_strategies`, and the LlamaIndex `content_atoms` table.
- User DB tables: `teacher_profiles`, `class_artifacts`.
```bash
python check_tables.py
```

## Expected Outcome
- The content DB contains the ingested book structure + atoms.
- Pedagogy strategies exist in `pedagogy_strategies`.
- Search returns atoms scoped to the book and unit.
