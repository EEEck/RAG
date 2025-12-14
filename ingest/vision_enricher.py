import os
import json
import uuid
import asyncio
import base64
from typing import List, Dict, Any, Optional, Union

import psycopg
from psycopg.rows import dict_row
import fitz  # PyMuPDF
from pydantic_ai import BinaryContent

from llama_index.core.schema import TextNode
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding

from ingest.infra.connection import get_connection
from .models import ContentAtom
from app.agent_factory import create_agent
from app.config import get_settings

class VisionEnricher:
    def __init__(self, db_connection_string: Optional[str] = None):
        """
        Initializes the VisionEnricher.

        Args:
            db_connection_string: Optional connection string. If None, uses environment variables.
        """
        self.conn = get_connection()

        settings = get_settings()
        self.agent = create_agent(
            system_prompt="You are a helpful assistant.",
            model_override=settings.vlm_model
        )

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def find_pending_images(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Finds 'image_asset' atoms that do not have a corresponding 'image_desc' atom.
        """
        # Safer query:
        query = """
        SELECT id, text, metadata_ as metadata
        FROM data_content_atoms
        WHERE metadata_->>'atom_type' = 'image_asset'
          AND NOT EXISTS (
              SELECT 1
              FROM data_content_atoms AS ca2
              WHERE ca2.metadata_->>'atom_type' = 'image_desc'
              AND ca2.metadata_->>'referenced_image_atom_id' = data_content_atoms.id::text
          )
        LIMIT %s;
        """

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (limit,))
            return cur.fetchall()

    def crop_image_from_pdf(self, file_path: str, page_no: int, bbox: Union[List[float], Dict[str, Any]]) -> bytes:
        """
        Crops an image from a PDF page.
        """
        if not os.path.exists(file_path):
             # Try relative to repo root
             if os.path.exists(os.path.join(os.getcwd(), file_path)):
                 file_path = os.path.join(os.getcwd(), file_path)
             else:
                 raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(file_path)
        page_idx = page_no - 1
        if page_idx < 0 or page_idx >= len(doc):
             raise ValueError(f"Page number {page_no} out of range for {file_path}")

        page = doc[page_idx]

        if isinstance(bbox, dict):
            l, r = bbox.get('l', 0), bbox.get('r', 0)
            t, b = bbox.get('t', 0), bbox.get('b', 0)
            origin = bbox.get('coord_origin', 'BOTTOMLEFT')

            if origin == 'BOTTOMLEFT':
                height = page.rect.height
                y0 = height - t
                y1 = height - b
                rect = fitz.Rect(l, y0, r, y1)
            else:
                rect = fitz.Rect(l, t, r, b)
        else:
            rect = fitz.Rect(bbox)

        rect.normalize()
        pix = page.get_pixmap(clip=rect)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes

    def generate_image_description(self, image_bytes: bytes) -> str:
        """
        Generates a description for the image using the configured VLM Agent.
        """
        prompt = "Describe this image from an educational textbook in detail. Focus on the educational content, text, diagrams, and any visual cues relevant for a student. If there is text, transcribe it."

        try:
            result = self.agent.run_sync(
                [
                    prompt,
                    BinaryContent(data=image_bytes, media_type='image/png')
                ]
            )
            return result.data
        except Exception as e:
            print(f"Error calling VLM Agent: {e}")
            return "Error generating description."

    def save_descriptions(self, descriptions: List[Dict[str, Any]]):
        """
        Saves the generated descriptions as new content atoms.
        """
        nodes = []
        for item in descriptions:
            new_metadata = item['metadata'].copy()
            new_metadata.update({
                "atom_type": "image_desc",
                "referenced_image_atom_id": str(item['parent_atom_id']),
            })

            node = TextNode(
                text=item['description'],
                metadata=new_metadata
            )
            nodes.append(node)

        if not nodes:
            return

        vector_store = PGVectorStore.from_params(
            database=os.getenv("POSTGRES_DB", "rag"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            password=os.getenv("POSTGRES_PASSWORD", "rag"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER", "rag"),
            table_name="content_atoms",
            embed_dim=1536
        )

        embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        VectorStoreIndex(
            nodes,
            storage_context=storage_context,
            embed_model=embed_model
        )
        print(f"Saved {len(nodes)} image descriptions to DB.")

    def process_batch(self, batch_size: int = 10):
        print(f"Checking for pending images (batch_size={batch_size})...")
        pending_atoms = self.find_pending_images(limit=batch_size)

        if not pending_atoms:
            print("No pending images found.")
            return

        print(f"Found {len(pending_atoms)} pending images.")

        descriptions_to_save = []

        for atom in pending_atoms:
            try:
                meta = atom['metadata']
                atom_id = atom['id']
                file_path = meta.get('file_path')
                bbox = meta.get('bbox')
                page_no = meta.get('page') or meta.get('page_no')

                if not file_path or not bbox or page_no is None:
                    print(f"Skipping atom {atom_id}: Missing metadata (file/bbox/page).")
                    continue

                print(f"Processing atom {atom_id} from {file_path} page {page_no}...")

                image_bytes = self.crop_image_from_pdf(file_path, int(page_no), bbox)
                description = self.generate_image_description(image_bytes)

                descriptions_to_save.append({
                    "parent_atom_id": atom_id,
                    "book_id": meta.get('book_id'),
                    "description": description,
                    "metadata": meta
                })

            except Exception as e:
                print(f"Error processing atom {atom['id']}: {e}")

        if descriptions_to_save:
            self.save_descriptions(descriptions_to_save)

if __name__ == "__main__":
    import sys
    enricher = VisionEnricher()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    enricher.process_batch(batch_size=limit)
