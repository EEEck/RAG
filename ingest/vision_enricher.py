import os
import json
import uuid
import asyncio
import base64
from typing import List, Dict, Any, Optional, Union

import psycopg
from psycopg.rows import dict_row
import fitz  # PyMuPDF
from openai import OpenAI

from llama_index.core.schema import TextNode
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding

from .db import get_db_connection
from .models import ContentAtom

class VisionEnricher:
    def __init__(self, db_connection_string: Optional[str] = None):
        """
        Initializes the VisionEnricher.

        Args:
            db_connection_string: Optional connection string. If None, uses environment variables.
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # We use a separate connection for raw queries
        self.conn = get_db_connection()

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def find_pending_images(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Finds 'image_asset' atoms that do not have a corresponding 'image_desc' atom.

        Returns:
            List of dicts representing the rows from content_atoms table.
        """
        query = """
        SELECT id, text, metadata_ as metadata
        FROM content_atoms
        WHERE metadata_->>'atom_type' = 'image_asset'
          AND id NOT IN (
              SELECT (metadata_->>'referenced_image_atom_id')::uuid
              FROM content_atoms
              WHERE metadata_->>'atom_type' = 'image_desc'
              AND metadata_->>'referenced_image_atom_id' IS NOT NULL
          )
        LIMIT %s;
        """
        # Note: 'id' in content_atoms is usually a VARCHAR/UUID. LlamaIndex stores it as VARCHAR usually,
        # but PGVectorStore schema might use UUID type if configured.
        # ingest/db.py schema shows structure_nodes uses UUID.
        # ingest/pipeline.py uses PGVectorStore. usually it creates a table with `id` as varchar or uuid depending on version.
        # Let's assume it handles the cast or comparison correctly.
        # If 'id' is varchar, the cast `::uuid` might be needed if the stored json value is a string representation.

        # We need to check if 'id' is UUID or VARCHAR in the actual DB.
        # Since I can't check, I'll write the query carefully.
        # If id is varchar, we should cast the right side to varchar.

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

        Args:
            file_path: Path to the PDF file.
            page_no: Page number (1-based index).
            bbox: Bounding box. Can be a list [x0, y0, x1, y1] or a Docling dictionary
                  {'l': ..., 't': ..., 'r': ..., 'b': ..., 'coord_origin': ...}.
        """
        if not os.path.exists(file_path):
             # Try relative to repo root
             if os.path.exists(os.path.join(os.getcwd(), file_path)):
                 file_path = os.path.join(os.getcwd(), file_path)
             else:
                 raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(file_path)
        # Docling page_no is likely 1-based. PyMuPDF is 0-based.
        page_idx = page_no - 1
        if page_idx < 0 or page_idx >= len(doc):
             raise ValueError(f"Page number {page_no} out of range for {file_path}")

        page = doc[page_idx]

        # Create rectangle. PyMuPDF expects (x0, y0, x1, y1) in TOP-LEFT origin.
        if isinstance(bbox, dict):
            # Handle Docling format
            # Example: {'l': 0.836, 't': 3257.291, 'r': 1812.423, 'b': 1606.586, 'coord_origin': 'BOTTOMLEFT'}
            l, r = bbox.get('l', 0), bbox.get('r', 0)
            t, b = bbox.get('t', 0), bbox.get('b', 0)
            origin = bbox.get('coord_origin', 'BOTTOMLEFT')

            if origin == 'BOTTOMLEFT':
                # Convert to TOPLEFT
                # PDF Height is needed.
                # page.rect.height gives the height in PDF points usually.
                height = page.rect.height

                # In Bottom-Left: y=0 is bottom.
                # 't' (top) is further from bottom (larger value).
                # 'b' (bottom) is closer to bottom (smaller value).

                # In Top-Left: y=0 is top.
                # New Top = Height - Old Top
                # New Bottom = Height - Old Bottom

                y0 = height - t
                y1 = height - b

                # PyMuPDF Rect(x0, y0, x1, y1)
                rect = fitz.Rect(l, y0, r, y1)
            else:
                # Assume TOPLEFT or unhandled, use directly but map keys
                rect = fitz.Rect(l, t, r, b)
        else:
            # Assume list [x0, y0, x1, y1] in correct coordinate system
            rect = fitz.Rect(bbox)

        # Normalize rect to ensure x0<x1, y0<y1
        rect.normalize()

        # Get pixmap (crop)
        pix = page.get_pixmap(clip=rect)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes

    def generate_image_description(self, image_bytes: bytes) -> str:
        """
        Generates a description for the image using OpenAI GPT-4o.
        """
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image from an educational textbook in detail. Focus on the educational content, text, diagrams, and any visual cues relevant for a student. If there is text, transcribe it."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return "Error generating description."

    def save_descriptions(self, descriptions: List[Dict[str, Any]]):
        """
        Saves the generated descriptions as new content atoms.

        Args:
            descriptions: List of dicts containing:
                - parent_atom_id
                - book_id
                - description (text)
                - metadata (original metadata to propagate)
        """
        nodes = []
        for item in descriptions:
            # Create metadata for the new atom
            new_metadata = item['metadata'].copy()
            new_metadata.update({
                "atom_type": "image_desc",
                "referenced_image_atom_id": str(item['parent_atom_id']),
                # We retain book_id, node_id from parent
            })

            # Create TextNode (which becomes ContentAtom in DB)
            node = TextNode(
                text=item['description'],
                metadata=new_metadata
            )
            nodes.append(node)

        if not nodes:
            return

        # Use the same persistence logic as pipeline.py
        vector_store = PGVectorStore.from_params(
            database=os.getenv("POSTGRES_DB", "rag"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            password=os.getenv("POSTGRES_PASSWORD", "rag"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER", "rag"),
            table_name="content_atoms",
            embed_dim=1536
        )

        # We need embeddings for these descriptions so they are searchable!
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
    # Simple CLI entry point
    import sys
    enricher = VisionEnricher()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    enricher.process_batch(batch_size=limit)
