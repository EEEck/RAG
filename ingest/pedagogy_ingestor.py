import json
import uuid
import os
from typing import Optional, List, Dict, Any

from app.schemas import PedagogyStrategy
from ingest.infra.connection import get_connection

# For MVP, we might use a simple OpenAI call to extract metadata + summary
# And another to get embedding.
# We will use `openai` library if available, otherwise mock or fail.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class PedagogyIngestor:
    """
    Ingests pedagogical guides (PDFs) into the `pedagogy_strategies` table.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if OpenAI and os.getenv("OPENAI_API_KEY") else None

    def ingest_guide(self, file_path: str, title_override: Optional[str] = None) -> str:
        """
        Parses the PDF, extracts metadata/strategy, and saves to DB.
        Returns the new strategy ID.
        """
        # 1. Parse Text (Simple extraction for MVP)
        # Using a simple text extraction. For production, use Docling.
        text_content = self._extract_text_from_pdf(file_path)

        # 2. Extract Metadata & Strategy via LLM
        if not title_override:
            title_override = os.path.basename(file_path)

        extraction = self._extract_metadata_and_strategy(text_content, title_override)

        # 3. Generate Embedding
        summary = extraction.get("summary", "")
        embedding = self._get_embedding(summary)

        # 4. Save to DB
        strategy_id = str(uuid.uuid4())

        strategy = PedagogyStrategy(
            id=strategy_id,
            title=extraction.get("title", title_override),
            subject=extraction.get("subject", "General"),
            min_grade=extraction.get("min_grade", 0),
            max_grade=extraction.get("max_grade", 12),
            institution_type=extraction.get("institution_type", "General"),
            prompt_injection=extraction.get("prompt_injection", ""),
            summary_for_search=summary
        )

        self._save_to_db(strategy, embedding)
        return strategy_id

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Simple wrapper to extract text. Uses pymupdf if available.
        """
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except ImportError:
            # Fallback for environments without pymupdf (or mock)
            # In a real scenario, this is critical.
            print("Warning: PyMuPDF (fitz) not found. Returning dummy text.")
            return "Dummy text content from PDF."
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return "Error reading PDF."

    def _extract_metadata_and_strategy(self, text: str, title: str) -> Dict[str, Any]:
        """
        Uses LLM to structured-extraction.
        """
        if not self.client:
            # Fallback / Mock
            return {
                "title": title,
                "subject": "English",
                "min_grade": 5,
                "max_grade": 10,
                "institution_type": "Gymnasium",
                "prompt_injection": "Use a supportive, encouraging tone. Focus on communicative competence.",
                "summary": f"A guide about {title} focusing on English teaching."
            }

        prompt = f"""
        You are an expert curriculum analyzer. Analyze the following text from a teaching guide ('{title}').

        Extract the following fields in JSON format:
        - title: The official title of the guide.
        - subject: The subject matter (e.g., English, Math).
        - min_grade: Minimum target grade (integer).
        - max_grade: Maximum target grade (integer).
        - institution_type: School type (e.g., Gymnasium, Primary School).
        - prompt_injection: A concise paragraph (system instruction) summarizing the core pedagogical principles to be injected into an AI tutor.
        - summary: A short summary of the document for search indexing.

        TEXT CONTENT (truncated):
        {text[:4000]}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "You are a JSON extractor."},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"LLM Extraction failed: {e}")
            return {
                "title": title,
                "subject": "Unknown",
                "prompt_injection": "Error extracting strategy.",
                "summary": "Error extracting strategy."
            }

    def _get_embedding(self, text: str) -> List[float]:
        """
        Generates embedding for the summary.
        """
        if not self.client:
            return [0.0] * 1536 # Mock embedding

        try:
            resp = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return resp.data[0].embedding
        except Exception as e:
            print(f"Embedding failed: {e}")
            return [0.0] * 1536

    def _save_to_db(self, strategy: PedagogyStrategy, embedding: List[float]) -> None:
        """
        Persists the strategy to Postgres.
        """
        query = """
        INSERT INTO pedagogy_strategies (
            id, title, subject, min_grade, max_grade, institution_type,
            prompt_injection, embedding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        # prompt_injection might be a dict or string.
        injection_json = json.dumps(strategy.prompt_injection) if isinstance(strategy.prompt_injection, (dict, list)) else json.dumps(strategy.prompt_injection)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    strategy.id,
                    strategy.title,
                    strategy.subject,
                    strategy.min_grade,
                    strategy.max_grade,
                    strategy.institution_type,
                    injection_json,
                    json.dumps(embedding) # pgvector usually handles list, but psycopg adapter might need tweaks.
                    # Actually, standard pgvector usage with psycopg3 is list.
                    # Let's try passing list directly first.
                ))
            conn.commit()
