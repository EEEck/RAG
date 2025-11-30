import os
import json
from typing import Literal, Dict, Any
from openai import OpenAI

def detect_book_metadata(title: str, sample_text: str = "") -> Dict[str, Any]:
    """
    Detects the category and grade level of a book based on its title and a sample of text.
    Returns a dictionary with 'subject' (category) and 'grade_level'.
    Defaults to 'language' and grade 1 if uncertain.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found. Defaulting to 'language' and grade 1.")
        return {"subject": "language", "grade_level": 1}

    client = OpenAI(api_key=api_key)

    prompt = f"""
    Analyze the following textbook metadata and return a JSON object with:
    1. "subject": One of ["language", "stem", "history"]
    2. "grade_level": An integer (1-12) representing the likely grade level.

    Book Title: "{title}"
    Text Sample (first few lines): "{sample_text[:500]}"

    Return ONLY raw JSON. No markdown formatting.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")

        data = json.loads(content)

        subject = data.get("subject", "language").lower()
        if subject not in ["language", "stem", "history"]:
            subject = "language"

        grade_level = data.get("grade_level", 1)
        if isinstance(grade_level, str) and grade_level.isdigit():
            grade_level = int(grade_level)
        if not isinstance(grade_level, int):
            grade_level = 1

        return {"subject": subject, "grade_level": grade_level}

    except Exception as e:
        print(f"Error analyzing book metadata: {e}. Defaulting to 'language' grade 1.")
        return {"subject": "language", "grade_level": 1}

def detect_book_category(title: str, sample_text: str = "") -> Literal["language", "stem", "history"]:
    """
    Wrapper for backward compatibility. Returns only the category string.
    """
    metadata = detect_book_metadata(title, sample_text)
    return metadata["subject"]
