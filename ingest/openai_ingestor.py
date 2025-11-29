import asyncio
import os
import json
import base64
from typing import List, Optional, Dict, Type, Union, Literal
from pydantic import BaseModel, Field
import fitz  # PyMuPDF
from openai import AsyncOpenAI
from .schemas import LanguageMetadata, STEMMetadata, HistoryMetadata, BaseMetadata

# --- Configuration ---
MODEL_NAME = "gpt-4o"
MAX_CONCURRENT_PAGES = 5

# --- Helper to create dynamic models ---
def create_page_model(metadata_cls: Type[BaseMetadata]):
    class SpecificAtomModel(BaseModel):
        content: str = Field(..., description="The actual text content, image description, or latex equation")
        meta_data: metadata_cls = Field(..., description="Domain specific metadata including content_type")

    class SpecificPageModel(BaseModel):
        unit_number: Optional[int] = Field(None, description="The unit number this page belongs to")
        lesson_title: Optional[str] = Field(None, description="The title of the lesson or section")
        atoms: List[SpecificAtomModel] = Field(..., description="List of extracted content blocks")

    return SpecificPageModel

# --- The Ingestor Class ---
class OpenAIIngestor:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)

    def _pdf_page_to_base64_image(self, doc, page_num):
        """Converts a PDF page to a base64 encoded JPEG image."""
        page = doc.load_page(page_num)
        # dpi=150 is usually sufficient for OCR and keeps token count lower
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("jpeg")
        return base64.b64encode(img_data).decode('utf-8')

    async def process_page(self, page_num: int, b64_image: str, category: str = "language") -> dict:
        """Sends one page image to OpenAI and requests structured JSON."""

        # Select Schema
        if category == "stem":
            metadata_cls = STEMMetadata
        elif category == "history":
            metadata_cls = HistoryMetadata
        else:
            metadata_cls = LanguageMetadata

        PageModel = create_page_model(metadata_cls)

        prompt = f"""
        You are an expert Educational Content Parser for {category} textbooks.
        Analyze this textbook page image. Extract the content into a structured format.

        Guidelines:
        1. Identify the Unit Number and Lesson Title from headers.
        2. Extract text blocks.
        3. Populate the 'meta_data' fields strictly according to the schema for {category}.
           - content_type must be one of: "text", "image", "exercise", "table", "vocab", "image_desc", "grammar", "equation"
        4. For images, write a detailed visual description in 'content' and set content_type to 'image_desc'.
        5. Ignore page numbers, headers, and copyright text in the main content (but capture unit/title).
        """

        async with self.semaphore:
            try:
                response = await self.client.beta.chat.completions.parse(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that extracts structured data from document images."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    response_format=PageModel
                )

                # The response is parsed into the Pydantic model
                page_content = response.choices[0].message.parsed

                return {
                    "page_number": page_num + 1,
                    "status": "success",
                    "data": page_content
                }

            except Exception as e:
                print(f"Error processing page {page_num + 1}: {e}")
                return {
                    "page_number": page_num + 1,
                    "status": "error",
                    "error": str(e)
                }

    async def ingest_book(self, pdf_path: str, category: str = "language"):
        """Main entry point to ingest a PDF."""
        print(f"Opening {pdf_path}...")
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"Found {total_pages} pages. Starting ingestion with {MODEL_NAME} for category: {category}...")

        tasks = []
        for i in range(total_pages):
            # Prepare the image locally (fast)
            b64_img = self._pdf_page_to_base64_image(doc, i)
            # Schedule the API call
            tasks.append(self.process_page(i, b64_img, category))

        # Run all tasks concurrently (controlled by semaphore)
        results = await asyncio.gather(*tasks)

        # Close PDF
        doc.close()

        valid_pages = [r for r in results if r['status'] == 'success']
        print(f"\nSuccessfully processed {len(valid_pages)}/{total_pages} pages.")

        return valid_pages
