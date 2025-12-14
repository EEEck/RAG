import asyncio
import os
import json
import base64
from typing import List, Optional, Dict, Type, Union, Literal
from pydantic import BaseModel, Field
import fitz  # PyMuPDF
from pydantic_ai import BinaryContent
from app.agent_factory import create_agent
from app.config import get_settings
from .schemas import LanguageMetadata, STEMMetadata, HistoryMetadata, BaseMetadata

# --- Configuration ---
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
        # API key is now handled by pydantic-ai via env vars or config,
        # but we keep signature for compatibility or remove it.
        # The caller (IngestionService) might pass it.
        # We can ignore it if pydantic-ai handles it.
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)

    def _pdf_page_to_bytes(self, doc, page_num) -> bytes:
        """Converts a PDF page to JPEG bytes."""
        page = doc.load_page(page_num)
        # dpi=150 is usually sufficient for OCR and keeps token count lower
        pix = page.get_pixmap(dpi=150)
        return pix.tobytes("jpeg")

    async def process_page(self, agent, page_num: int, image_bytes: bytes, prompt: str) -> dict:
        """Sends one page image to Agent."""

        async with self.semaphore:
            try:
                # PydanticAI VLM call
                result = await agent.run(
                    [
                        prompt,
                        BinaryContent(data=image_bytes, media_type='image/jpeg')
                    ]
                )

                page_content = result.data

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

        settings = get_settings()
        print(f"Found {total_pages} pages. Starting ingestion with {settings.vlm_model} for category: {category}...")

        # 1. Determine Model
        if category == "stem":
            metadata_cls = STEMMetadata
        elif category == "history":
            metadata_cls = HistoryMetadata
        else:
            metadata_cls = LanguageMetadata

        PageModel = create_page_model(metadata_cls)

        # 2. Create Agent
        system_prompt = "You are a helpful assistant that extracts structured data from document images."
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

        agent = create_agent(
            result_type=PageModel,
            system_prompt=system_prompt,
            model_override=settings.vlm_model
        )

        tasks = []
        for i in range(total_pages):
            # Prepare the image locally
            img_bytes = self._pdf_page_to_bytes(doc, i)
            # Schedule the API call
            tasks.append(self.process_page(agent, i, img_bytes, prompt))

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Close PDF
        doc.close()

        valid_pages = [r for r in results if r['status'] == 'success']
        print(f"\nSuccessfully processed {len(valid_pages)}/{total_pages} pages.")

        return valid_pages
