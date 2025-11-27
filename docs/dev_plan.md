# **Project: Scalable Textbook RAG (MVP)**

**Timeline:** 4 Weeks

**Goal:** Deploy a production-ready RAG system that ingests ESL/Science textbooks, enforces strict curriculum safety (Unit 1 concepts only), and scales to 100+ concurrent users via database partitioning.

## **1\. Core User Stories**

| Actor | Story | Acceptance Criteria |
| :---- | :---- | :---- |
| **Admin** | As an admin, I want to upload a PDF (e.g., "Green Line 1") and have it automatically ingested, partitioned, and indexed. | System creates a new DB partition content\_book\_{id}, runs Docling, and populates vectors. |
| **Teacher** | As a teacher, I want to generate a quiz for **Unit 3** that *only* uses vocabulary/grammar from Units 1-3. | API query includes WHERE unit\_id \<= 3\. Result contains zero concepts from Unit 4+. |
| **Teacher** | As a teacher, I want to select my specific textbook profile so I don't get search results from unrelated books. | API requests are routed *only* to the partition corresponding to the teacher's selected book\_id. |
| **System** | As a platform, I need to handle 100 teachers clicking "Generate" simultaneously without crashing. | Requests are queued via Celery/Redis; Users receive a job\_id and poll for results. |

## **2\. High-Level Architecture**

### **The Stack**

* **Ingestion:** Python Worker (Docling for layout \+ LlamaParse for complex fallback).  
* **Database:** PostgreSQL 16+ (Managed) with pgvector.  
  * *Strategy:* **List Partitioning** by book\_id.  
* **API Layer:** FastAPI (Async).  
* **Async Queue:** Redis (Broker) \+ Celery (Workers).  
* **Caching:** Redis (Semantic Cache).  
* **LLM:** Gemini Flash 1.5 (Fast/Cheap) for description/generation.

## **3\. The Universal Database Schema (Partitioned)**

This schema supports ESL (text/images) and Math/Physics (LaTeX equations) equally.

\-- Enable Extensions  
CREATE EXTENSION IF NOT EXISTS vector;

\-- 1\. Structure Nodes (The Table of Contents)  
\-- Stores the hierarchy: Book \-\> Unit \-\> Lesson \-\> Exercise  
CREATE TABLE structure\_nodes (  
    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    book\_id UUID NOT NULL,  
    parent\_id UUID REFERENCES structure\_nodes(id),  
    node\_level INTEGER, \-- 0=Book, 1=Unit, 2=Section  
    title TEXT,  
    sequence\_index INTEGER, \-- Vital for "Curriculum Safety" (Unit 1 \< Unit 2\)  
    meta\_data JSONB \-- {"page\_start": 10, "page\_end": 12}  
);

\-- 2\. Content Atoms (Partitioned Parent Table)  
\-- This table is virtually empty. Data lives in child tables.  
CREATE TABLE content\_atoms (  
    id UUID,  
    book\_id UUID NOT NULL, \-- PARTITION KEY  
    node\_id UUID,          \-- Link to Structure  
    atom\_type VARCHAR(50), \-- 'text', 'image\_desc', 'equation\_latex', 'vocab\_card'  
    content\_text TEXT,  
    embedding vector(768), \-- Gemini Flash Embedding Dimension  
    meta\_data JSONB,       \-- {"cefr": "A1", "complexity": "hard"}  
    PRIMARY KEY (id, book\_id)  
) PARTITION BY LIST (book\_id);

\-- 3\. Function to Auto-Create Partitions (Run this on book ingestion)  
CREATE OR REPLACE FUNCTION create\_book\_partition(new\_book\_id UUID)   
RETURNS VOID AS $$  
DECLARE  
    partition\_name TEXT;  
BEGIN  
    partition\_name := 'content\_book\_' || replace(new\_book\_id::text, '-', '\_');  
    EXECUTE format(  
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF content\_atoms FOR VALUES IN (%L)',   
        partition\_name, new\_book\_id  
    );  
    \-- Create specific index for this book's subspace  
    EXECUTE format(  
        'CREATE INDEX ON %I USING hnsw (embedding vector\_cosine\_ops)',   
        partition\_name  
    );  
END;  
$$ LANGUAGE plpgsql;

## **4\. The Hybrid Ingestion Pipeline (Python)**

This router logic handles the "Clean Layout" vs. "Complex Syntax" trade-off.

import os  
from docling.document\_converter import DocumentConverter  
from llama\_parse import LlamaParse

class HybridIngestor:  
    def \_\_init\_\_(self):  
        self.docling \= DocumentConverter()  
        self.llama \= LlamaParse(result\_type="markdown", api\_key=os.getenv("LLAMA\_CLOUD\_API\_KEY"))

    def ingest\_book(self, file\_path: str):  
        \# Step 1: Try Fast/Local Ingestion first (Docling)  
        print(f"Starting Docling for {file\_path}...")  
        doc \= self.docling.convert(file\_path)  
        data \= doc.document.export\_to\_dict()  
          
        \# Step 2: Quality Gate / Router  
        \# If we detect complex tables are empty or math is garbled, fallback.  
        if self.\_needs\_fallback(data):  
            print("Complexity detected (Math/Tables). Switching to LlamaParse...")  
            return self.ingest\_with\_llama(file\_path)  
          
        return self.\_parse\_docling\_structure(data)

    def \_needs\_fallback(self, data) \-\> bool:  
        \# Heuristic: If \>20% of tables have no text, or heavily nested structures found  
        empty\_tables \= \[t for t in data.get('tables', \[\]) if not t.get('data')\]  
        return len(empty\_tables) \> 5

    def ingest\_with\_llama(self, file\_path):  
        \# Uses Vision-LLM to parse complex layouts/math  
        documents \= self.llama.load\_data(file\_path)  
        return \[{"type": "complex\_page", "text": d.text} for d in documents\]

    def \_parse\_docling\_structure(self, data):  
        \# (Insert the "Walker Script" logic here from previous discussion)  
        \# Maps Docling Headers \-\> DB structure\_nodes  
        \# Maps Text/Images \-\> DB content\_atoms  
        pass

## **5\. API & Scaling Architecture**

To handle "Thundering Herds" (30 teachers clicking 'Generate' at once), we use an Asynchronous Queue pattern.

### **The Stack Implementation**

1. **FastAPI** receives the request.  
2. **Redis** stores the job status (pending).  
3. **Celery Worker** picks up the heavy RAG task.  
4. **Frontend** polls /job/{id} every 2 seconds.

### **Code Pattern (FastAPI \+ Celery)**

\# main.py (FastAPI)  
from fastapi import FastAPI  
from celery\_worker import generate\_quiz\_task  
import uuid

app \= FastAPI()

@app.post("/generate/quiz")  
async def start\_quiz\_generation(book\_id: str, unit: int, topic: str):  
    job\_id \= str(uuid.uuid4())  
    \# Send to Redis Queue \- Returns immediately (Non-blocking)  
    task \= generate\_quiz\_task.delay(job\_id, book\_id, unit, topic)  
    return {"job\_id": job\_id, "status": "queued"}

@app.get("/jobs/{job\_id}")  
async def get\_job\_status(job\_id: str):  
    \# Check Redis for result  
    result \= AsyncResult(job\_id)  
    if result.state \== 'PENDING':  
        return {"status": "processing"}  
    elif result.state \== 'SUCCESS':  
        return {"status": "complete", "data": result.result}

\# celery\_worker.py (The heavy lifter)  
from celery import Celery  
from rag\_engine import retrieve\_and\_generate

celery \= Celery(\_\_name\_\_, broker="redis://localhost:6379/0")

@celery.task  
def generate\_quiz\_task(job\_id, book\_id, unit, topic):  
    \# 1\. Connect to Specific DB Partition  
    \# 2\. Run Vector Search (WHERE unit\_id \<= unit)  
    \# 3\. Call Gemini API  
    result \= retrieve\_and\_generate(book\_id, unit, topic)  
    return result

## **6\. Implementation Roadmap (4 Weeks)**

### **Week 1: The "Data Foundation"**

* \[ \] **Infra:** Set up Postgres (pgvector) and Redis locally via Docker Compose.  
* \[ \] **Schema:** Run the SQL DDL for structure\_nodes and content\_atoms.  
* \[ \] **Ingestion:** Implement the HybridIngestor class.  
  * *Task:* Run it on "Green Line 1" PDF.  
  * *Task:* Verify images are extracted and linked to "Unit 1".

### **Week 2: The "Enrichment Engine"**

* \[ \] **Vision AI:** Write script to iterate image\_assets, send to Gemini Flash, and save descriptions to content\_atoms (type=image\_desc).  
* \[ \] **Curriculum Guard:** Write the SQL query template that strictly enforces WHERE sequence\_index \<= X.  
* \[ \] **Embeddings:** Batch embed all text chunks using Gemini Embedding API.

### **Week 3: The "Scalable API"**

* \[ \] **Queueing:** Implement the FastAPI \+ Celery pattern (code above).  
* \[ \] **Caching:** Add a Redis check before calling Celery.  
  * key \= f"quiz:{book\_id}:{unit}:{topic}".  
* \[ \] **Partitioning:** Test the create\_book\_partition function by ingesting a second dummy book.

### **Week 4: The "Frontend & Pilot"**

* \[ \] **UI:** Simple React/Streamlit app.  
  * *Profile Selector:* Dropdown to pick "Green Line 1".  
  * *Action:* "Generate Quiz for Unit 5".  
* \[ \] **Load Test:** Simulate 50 concurrent requests to ensure Celery queues work.  
* \[ \] **Deploy:** Push to Cloud Run (API) \+ Neon/Supabase (DB).

## **7\. Edge Case Handling**

| Scenario | Risk | Mitigation Strategy |
| :---- | :---- | :---- |
| **User selects 10 books** | Database load explodes searching 10 partitions. | **Hard Limit:** UI allows max 2 active books per session. |
| **"Hallucinations"** | LLM generates concepts not in the book. | **Prompt Engineering:** "You are a Strict Librarian. Only use the provided Context. If context is missing, say 'I cannot generate this'." |
| **Math Equations** | Docling output is messy for complex formulas. | **Router Logic:** If content\_atoms contains $ symbols but is malformed, flag for re-ingestion via LlamaParse. |

