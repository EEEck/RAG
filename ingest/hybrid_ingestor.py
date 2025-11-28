import os
import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple

# Stub for LlamaParse if not installed or configured
try:
    from llama_parse import LlamaParse
except ImportError:
    LlamaParse = None

from docling.document_converter import DocumentConverter

from .models import StructureNode, ContentAtom
from .openai_ingestor import OpenAIIngestor

class HybridIngestor:
    def __init__(self):
        self.docling = DocumentConverter()
        self.llama_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if self.llama_api_key and LlamaParse:
            self.llama = LlamaParse(result_type="markdown", api_key=self.llama_api_key)
        else:
            self.llama = None

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
             self.openai_ingestor = OpenAIIngestor(api_key=self.openai_api_key)
        else:
             self.openai_ingestor = None

    def ingest_book(self, file_path: str, book_id: uuid.UUID) -> Tuple[List[StructureNode], List[ContentAtom]]:
        print(f"Starting Docling for {file_path}...")
        try:
            doc = self.docling.convert(file_path)
            # Export to dict to analyze structure
            data = doc.document.export_to_dict()

            if self._needs_fallback(data):
                print("Complexity detected. Switching to LlamaParse...")
                try:
                    return self.ingest_with_llama(file_path, book_id)
                except Exception as e:
                    print(f"LlamaParse failed: {e}. Falling back to OpenAI VLM...")
                    return self.ingest_with_openai(file_path, book_id)

            # Check if Docling result is empty or poor quality which might indicate handwritten script
            if self._is_poor_quality_or_handwritten(data):
                 print("Docling result poor or handwritten script suspected. Falling back to OpenAI VLM...")
                 return self.ingest_with_openai(file_path, book_id)

            return self._parse_docling_structure(data, book_id)

        except Exception as e:
            print(f"Docling failed: {e}. Attempting OpenAI VLM fallback...")
            return self.ingest_with_openai(file_path, book_id)

    def _needs_fallback(self, data) -> bool:
        # Heuristic: If >20% of tables have no text, or heavily nested structures found
        tables = data.get('tables', [])
        if not tables:
            return False

        empty_tables = [t for t in tables if not t.get('data')]
        if len(tables) > 0 and (len(empty_tables) / len(tables)) > 0.2:
            return True
        return False

    def _is_poor_quality_or_handwritten(self, data) -> bool:
        # Heuristic: Very little text extracted relative to pages, or mostly empty structure
        # This is a simple placeholder heuristic.
        texts = data.get("texts", [])
        if len(texts) < 5: # Arbitrary low number for a whole book/script
            return True
        return False

    def ingest_with_llama(self, file_path: str, book_id: uuid.UUID) -> Tuple[List[StructureNode], List[ContentAtom]]:
        if not self.llama:
            # Fallback if key missing: raise error to trigger next fallback
            raise ValueError("LlamaParse not configured or key missing.")

        documents = self.llama.load_data(file_path)
        # LlamaParse returns flat markdown pages usually
        nodes = []
        atoms = []

        # Create a root node for the book
        root_id = uuid.uuid4()
        nodes.append(StructureNode(
            id=root_id,
            book_id=book_id,
            parent_id=None,
            node_level=0,
            title="Book Root",
            sequence_index=0,
            meta_data={}
        ))

        for idx, d in enumerate(documents):
            # Create a generic page/section node
            node_id = uuid.uuid4()
            nodes.append(StructureNode(
                id=node_id,
                book_id=book_id,
                parent_id=root_id,
                node_level=1,
                title=f"Section {idx+1}",
                sequence_index=idx+1,
                meta_data={"page": idx+1}
            ))

            atoms.append(ContentAtom(
                id=uuid.uuid4(),
                book_id=book_id,
                node_id=node_id,
                atom_type="complex_page",
                content_text=d.text,
                meta_data={}
            ))

        return nodes, atoms

    def ingest_with_openai(self, file_path: str, book_id: uuid.UUID) -> Tuple[List[StructureNode], List[ContentAtom]]:
        if not self.openai_ingestor:
             raise ValueError("OpenAI API Key not set. Cannot use OpenAI Fallback.")

        print(f"Starting OpenAI VLM ingestion for {file_path}...")
        # Run async ingestion synchronously
        pages_data = asyncio.run(self.openai_ingestor.ingest_book(file_path))

        nodes = []
        atoms = []

        # Create a root node for the book
        root_id = uuid.uuid4()
        nodes.append(StructureNode(
            id=root_id,
            book_id=book_id,
            parent_id=None,
            node_level=0,
            title="Book Root (OpenAI)",
            sequence_index=0,
            meta_data={"source": "openai-vlm"}
        ))

        sequence_counter = 0

        for page_result in pages_data:
            data = page_result['data'] # This is a PageContentModel Pydantic object
            page_num = page_result['page_number']

            # Create a Node for the Unit/Lesson or Page
            node_id = uuid.uuid4()
            sequence_counter += 1

            # Determine title
            title = f"Page {page_num}"
            if data.lesson_title:
                title = data.lesson_title
            elif data.unit_number is not None:
                title = f"Unit {data.unit_number}"

            nodes.append(StructureNode(
                id=node_id,
                book_id=book_id,
                parent_id=root_id,
                node_level=1,
                title=title,
                sequence_index=sequence_counter,
                meta_data={
                    "page": page_num,
                    "unit": data.unit_number,
                    "lesson": data.lesson_title
                }
            ))

            # Process atoms
            for atom_model in data.atoms:
                atom_id = uuid.uuid4()
                atoms.append(ContentAtom(
                    id=atom_id,
                    book_id=book_id,
                    node_id=node_id,
                    atom_type=atom_model.type,
                    content_text=atom_model.content,
                    meta_data=atom_model.meta_data or {}
                ))

        return nodes, atoms

    def _parse_docling_structure(self, data: Dict, book_id: uuid.UUID) -> Tuple[List[StructureNode], List[ContentAtom]]:
        # Maps Docling Headers -> DB structure_nodes
        # Maps Text/Images -> DB content_atoms

        nodes = []
        atoms = []

        # Root node
        root_id = uuid.uuid4()
        nodes.append(StructureNode(
            id=root_id,
            book_id=book_id,
            parent_id=None,
            node_level=0,
            title="Book Root",
            sequence_index=0,
            meta_data={}
        ))

        current_parents = {0: root_id} # level -> id
        last_node_id = root_id
        sequence = 0

        # Docling 2.0+ structure might differ, relying on 'texts' list as a flat stream
        for item in data.get("texts", []):
            label = item.get("label", "text")
            text = item.get("text", "").strip()
            level = item.get("level")

            if not text:
                continue

            if label in ["title", "section_header", "header"]:
                node_level = level if level is not None else 1
                if node_level == 0: node_level = 1

                # Find parent
                parent_level = node_level - 1
                while parent_level >= 0 and parent_level not in current_parents:
                    parent_level -= 1

                if parent_level < 0:
                    parent_id = root_id
                else:
                    parent_id = current_parents[parent_level]

                new_node_id = uuid.uuid4()
                sequence += 1

                prov = item.get("prov", [])
                meta_data = prov[0] if prov else {}

                node = StructureNode(
                    id=new_node_id,
                    book_id=book_id,
                    parent_id=parent_id,
                    node_level=node_level,
                    title=text[:200],
                    sequence_index=sequence,
                    meta_data=meta_data
                )
                nodes.append(node)
                current_parents[node_level] = new_node_id
                last_node_id = new_node_id

            else:
                # Content Atom
                atom = ContentAtom(
                    id=uuid.uuid4(),
                    book_id=book_id,
                    node_id=last_node_id,
                    atom_type="text",
                    content_text=text,
                    meta_data={"label": label, "prov": item.get("prov")}
                )
                atoms.append(atom)

        return nodes, atoms
