import json
import os
from typing import List, Optional

from app.schemas import PedagogyStrategy
from ingest.infra.connection import get_connection

# Re-use connection logic
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class PedagogyService:
    """
    Service for searching pedagogical strategies and synthesizing system prompts.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if OpenAI and os.getenv("OPENAI_API_KEY") else None

    def search_strategies(
        self,
        query: str,
        subject: Optional[str] = None,
        grade: Optional[int] = None,
        limit: int = 3
    ) -> List[PedagogyStrategy]:
        """
        Searches for strategies by vector similarity + metadata filters.
        """
        query_vec = self._get_embedding(query)

        # Build SQL Query
        sql = """
        SELECT id, title, subject, min_grade, max_grade, institution_type, prompt_injection,
               embedding <=> %s::vector AS distance
        FROM pedagogy_strategies
        WHERE 1=1
        """
        params = [json.dumps(query_vec)]

        if subject:
            sql += " AND subject = %s"
            params.append(subject)

        if grade is not None:
            sql += " AND min_grade <= %s AND max_grade >= %s"
            params.append(grade)
            params.append(grade)

        sql += " ORDER BY distance ASC LIMIT %s"
        params.append(limit)

        with get_connection() as conn:
            # We need to register vector type or cast in SQL.
            # Psycopg 3 usually needs specific setup for vector types if passing list directly.
            # Using string representation '[1,2,3]' is safest generic way.

            # Correction: params[0] needs to be stringified list for %s::vector
            params[0] = str(query_vec)

            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        results = []
        for row in rows:
            # Row index depends on SELECT order
            # 0:id, 1:title, 2:subject, 3:min, 4:max, 5:inst, 6:prompt, 7:dist

            # Handle JSONB prompt_injection
            prompt_injection = row[6]
            # If driver returns dict, use it. If str, load it.
            if isinstance(prompt_injection, str):
                try:
                    prompt_injection = json.loads(prompt_injection)
                except:
                    pass

            results.append(PedagogyStrategy(
                id=str(row[0]),
                title=row[1],
                subject=row[2],
                min_grade=row[3],
                max_grade=row[4],
                institution_type=row[5],
                prompt_injection=prompt_injection,
                summary_for_search="" # Not fetching content for list
            ))

        return results

    def generate_pedagogy_prompt(self, strategies: List[PedagogyStrategy]) -> str:
        """
        Synthesizes multiple strategies into a single coherent system prompt block.
        """
        if not strategies:
            return "Use a standard, neutral teaching style."

        # Format the injections
        injections = []
        for s in strategies:
            content = s.prompt_injection
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
            injections.append(f"--- SOURCE: {s.title} ---\n{content}")

        combined_text = "\n\n".join(injections)

        return f"""
### SYSTEM INSTRUCTIONS (Pedagogical Context)

You are an AI assistant customized for the following specific teaching context.

**PEDAGOGICAL SOURCES:**
The following documents define your teaching style and curriculum standards:

{combined_text}

**INSTRUCTION:**
Synthesize these guidelines. If documents conflict, prioritize the official Curriculum (Lehrplan).
Ensure all generated content (quizzes, plans) aligns with the grade level and methods described above.
"""

    def _get_embedding(self, text: str) -> List[float]:
        """
        Helper to get query embedding.
        """
        if not self.client:
            return [0.0] * 1536

        try:
            resp = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return resp.data[0].embedding
        except Exception as e:
            print(f"Embedding failed: {e}")
            return [0.0] * 1536

# Factory
_pedagogy_service = PedagogyService()

def get_pedagogy_service() -> PedagogyService:
    return _pedagogy_service
