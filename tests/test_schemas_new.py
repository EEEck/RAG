import uuid
import pytest
from pydantic import ValidationError
from ingest.schemas import LanguageMetadata, STEMMetadata, HistoryMetadata
from ingest.models import ContentAtom

class TestSchemas:
    def test_language_metadata_valid(self):
        """Test valid LanguageMetadata creation."""
        meta = LanguageMetadata(
            book_id="123",
            unit_number=1,
            page_number=10,
            content_type="vocab",
            vocab_word="apple",
            word_class="noun"
        )
        assert meta.category == "language"
        assert meta.vocab_word == "apple"

    def test_stem_metadata_valid(self):
        """Test valid STEMMetadata creation."""
        meta = STEMMetadata(
            book_id="456",
            unit_number=2,
            page_number=20,
            content_type="equation",
            latex_formula="E=mc^2",
            is_solution=True
        )
        assert meta.category == "stem"
        assert meta.latex_formula == "E=mc^2"
        assert meta.is_solution is True

    def test_history_metadata_valid(self):
        """Test valid HistoryMetadata creation."""
        meta = HistoryMetadata(
            book_id="789",
            unit_number=3,
            page_number=30,
            content_type="text",
            era="Cold War",
            key_figures=["JFK", "Khrushchev"]
        )
        assert meta.category == "history"
        assert "JFK" in meta.key_figures

    def test_content_atom_with_nested_schema(self):
        """Test ContentAtom holding different metadata types."""
        book_id = uuid.uuid4()
        node_id = uuid.uuid4()

        # Language Atom
        lang_meta = LanguageMetadata(book_id=str(book_id), page_number=1, content_type="text")
        atom = ContentAtom(
            id=uuid.uuid4(),
            book_id=book_id,
            node_id=node_id,
            atom_type="text",
            content_text="Hello",
            meta_data=lang_meta
        )
        assert isinstance(atom.meta_data, LanguageMetadata)

        # STEM Atom
        stem_meta = STEMMetadata(book_id=str(book_id), page_number=2, content_type="equation")
        atom2 = ContentAtom(
            id=uuid.uuid4(),
            book_id=book_id,
            node_id=node_id,
            atom_type="equation",
            content_text="x=y",
            meta_data=stem_meta
        )
        assert isinstance(atom2.meta_data, STEMMetadata)

    def test_validation_error(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            LanguageMetadata(book_id="123") # Missing content_type

    def test_serialization(self):
        """Test model_dump serialization."""
        meta = STEMMetadata(
            book_id="123",
            page_number=5,
            content_type="text",
            difficulty="hard"
        )
        data = meta.model_dump()
        assert data["category"] == "stem"
        assert data["difficulty"] == "hard"
        assert data["content_type"] == "text"
