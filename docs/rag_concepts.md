# RAG Concepts & Background

## What is RAG?

**Retrieval-Augmented Generation (RAG)** is a technique used to enhance Large Language Models (LLMs) like GPT-4 by providing them with specific, private, or up-to-date data that they were not trained on.

### The Problem
Standard LLMs are "frozen" in time and lack access to your private documents. If you ask, "What does Unit 5 in *My Specific Textbook* say?", the LLM will hallucinate or say it doesn't know.

### The Solution
1.  **Retrieval**: When you ask a question, the system searches your database of documents for the most relevant paragraphs.
2.  **Augmentation**: The system combines your question + the found paragraphs into a prompt.
3.  **Generation**: The LLM answers your question using the retrieved information as facts.

---

## Key Technologies in This Project

### 1. Embeddings & Vector Databases
Computers don't understand meaning in text; they understand numbers.
*   **Embedding Model**: A model (like OpenAI's `text-embedding-3-small`) that converts text into a long list of numbers called a **Vector**. Similar texts have mathematically similar vectors.
*   **Vector Database (pgvector)**: A specialized database that can store these vectors and quickly find the "nearest neighbors" (most similar text) to a user's query.

### 2. Hybrid Ingestion
Converting a PDF textbook into clean text for an LLM is difficult because of layouts, images, and tables. This project uses a three-tiered approach:
*   **Docling**: A fast, local tool that extracts text and structure.
*   **LlamaParse**: A powerful cloud service used if the layout is too complex.
*   **OpenAI VLM**: If the page is handwritten or an image scan, we show the image to GPT-4o and ask it to transcribe it.

### 3. Content Atoms vs. Structure Nodes
We organize data in two ways:
*   **Structure Nodes**: Represent the "Table of Contents" (Unit 1 -> Lesson A). This helps us know *where* we are in the book.
*   **Content Atoms**: Small chunks of text (paragraphs, definitions) that are actually searched. By searching "atoms" but filtering by "nodes" (e.g., "only search in Unit 1"), we get precise results.
