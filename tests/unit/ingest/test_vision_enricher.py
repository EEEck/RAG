import pytest
from unittest.mock import MagicMock, patch
from ingest.vision_enricher import VisionEnricher

@patch("ingest.vision_enricher.get_connection")
@patch("ingest.vision_enricher.OpenAI")
def test_vision_enricher_init(mock_openai, mock_get_conn):
    enricher = VisionEnricher()
    mock_get_conn.assert_called_once()
    mock_openai.assert_called_once()

@patch("ingest.vision_enricher.get_connection")
@patch("ingest.vision_enricher.OpenAI")
def test_find_pending_images(mock_openai, mock_get_conn):
    enricher = VisionEnricher()
    mock_cur = MagicMock()
    enricher.conn.cursor.return_value.__enter__.return_value = mock_cur

    # Mock data
    mock_cur.fetchall.return_value = [{"id": "1", "text": "img", "metadata": {"atom_type": "image_asset"}}]

    pending = enricher.find_pending_images(limit=5)
    assert len(pending) == 1
    mock_cur.execute.assert_called_once()

@patch("ingest.vision_enricher.fitz.open")
@patch("ingest.vision_enricher.get_connection")
@patch("ingest.vision_enricher.OpenAI")
def test_crop_image_from_pdf(mock_openai, mock_get_conn, mock_fitz):
    enricher = VisionEnricher()
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 5
    mock_page = MagicMock()
    mock_doc.__getitem__.return_value = mock_page
    mock_fitz.return_value = mock_doc

    # Mock os.path.exists
    with patch("os.path.exists", return_value=True):
        # Mock pixmap.tobytes
        mock_page.get_pixmap.return_value.tobytes.return_value = b"image"

        img = enricher.crop_image_from_pdf("test.pdf", 1, [0,0,10,10])
        assert img == b"image"
        mock_page.get_pixmap.assert_called()

@patch("ingest.vision_enricher.get_connection")
@patch("ingest.vision_enricher.OpenAI")
def test_generate_image_description(mock_openai, mock_get_conn):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "Desc"

    enricher = VisionEnricher()
    desc = enricher.generate_image_description(b"img")
    assert desc == "Desc"
