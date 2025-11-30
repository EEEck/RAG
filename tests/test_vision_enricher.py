import os
import pytest
from unittest.mock import MagicMock, patch
import fitz
from ingest.vision_enricher import VisionEnricher

# Real PDF path
PDF_PATH = "data/toy_green_line_1.pdf"
# Bbox from docling json
DOCLING_BBOX = {
    "l": 0.8360595703125,
    "t": 3257.2913818359375,
    "r": 1812.423828125,
    "b": 1606.58642578125,
    "coord_origin": "BOTTOMLEFT"
}
PAGE_NO = 1

@pytest.fixture
def enricher():
    # Mock connection to avoid real DB access
    with patch("ingest.vision_enricher.get_connection") as mock_conn:
        with patch("ingest.vision_enricher.OpenAI") as mock_openai: # Mock OpenAI client init
             enricher = VisionEnricher()
             yield enricher

def test_crop_image_real_pdf(enricher):
    """
    Integration test using real PDF to verify cropping logic with Docling bbox.
    """
    if not os.path.exists(PDF_PATH):
        pytest.skip(f"Test PDF not found at {PDF_PATH}")

    image_bytes = enricher.crop_image_from_pdf(PDF_PATH, PAGE_NO, DOCLING_BBOX)
    assert image_bytes is not None
    assert len(image_bytes) > 0

    # Verify it is a valid image by checking signature (PNG)
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    assert image_bytes[:8] == b'\x89PNG\r\n\x1a\n'

@patch("ingest.vision_enricher.PGVectorStore")
@patch("ingest.vision_enricher.VectorStoreIndex")
@patch("ingest.vision_enricher.OpenAIEmbedding")
def test_full_flow_mocked(mock_embed, mock_index, mock_pg, enricher):
    # Mock find_pending_images
    enricher.find_pending_images = MagicMock(return_value=[
        {
            "id": "atom-1",
            "text": "Image Ref",
            "metadata": {
                "file_path": PDF_PATH,
                "bbox": DOCLING_BBOX,
                "page": PAGE_NO,
                "book_id": "book-1"
            }
        }
    ])

    # Mock crop_image to return dummy bytes
    # We mock the method on the instance
    original_crop = enricher.crop_image_from_pdf
    enricher.crop_image_from_pdf = MagicMock(return_value=b"fake_image_data")

    # Mock OpenAI generation
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="A nice diagram."))
    ]
    enricher.client.chat.completions.create.return_value = mock_response

    # Run process
    enricher.process_batch(batch_size=1)

    # Verify interactions
    enricher.crop_image_from_pdf.assert_called_once()
    enricher.client.chat.completions.create.assert_called_once()

    # Verify persistence
    assert mock_pg.from_params.called
    assert mock_index.called

    # Restore
    enricher.crop_image_from_pdf = original_crop
