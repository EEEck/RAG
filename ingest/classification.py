import os
from typing import Literal
from openai import OpenAI

def detect_book_category(title: str, sample_text: str = "") -> Literal["language", "stem", "history"]:
    """
    Detects the category of a book based on its title and a sample of text.
    Defaults to 'language' if uncertain.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found. Defaulting to 'language'.")
        return "language"

    client = OpenAI(api_key=api_key)

    prompt = f"""
    Classify the following textbook into one of these three categories:
    1. 'language' (ESL, grammar, vocabulary, reading comprehension)
    2. 'stem' (Math, Physics, Chemistry, Biology, Engineering)
    3. 'history' (History, Social Studies, Geography, Civics)

    Book Title: "{title}"
    Text Sample (first few lines): "{sample_text[:500]}"

    Return ONLY the category name in lowercase.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        category = response.choices[0].message.content.strip().lower()
        if category in ["language", "stem", "history"]:
            return category
        return "language" # Fallback
    except Exception as e:
        print(f"Error categorizing book: {e}. Defaulting to 'language'.")
        return "language"
