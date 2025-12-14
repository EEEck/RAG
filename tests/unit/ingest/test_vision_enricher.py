import pytest
from unittest.mock import MagicMock, patch
from ingest.vision_enricher import VisionEnricher
from pydantic_ai import BinaryContent

@patch("ingest.vision_enricher.get_connection")
@patch("ingest.vision_enricher.create_agent")
def test_vision_enricher_init(mock_create_agent, mock_get_conn):
    enricher = VisionEnricher()
    mock_get_conn.assert_called_once()
    mock_create_agent.assert_called_once()

@patch("ingest.vision_enricher.get_connection")
@patch("ingest.vision_enricher.create_agent")
def test_find_pending_images(mock_create_agent, mock_get_conn):
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
@patch("ingest.vision_enricher.create_agent")
def test_crop_image_from_pdf(mock_create_agent, mock_get_conn, mock_fitz):
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
@patch("ingest.vision_enricher.create_agent")
def test_generate_image_description(mock_create_agent, mock_get_conn):
    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    # Mock result
    mock_result = MagicMock()
    mock_result.data = "Desc"
    mock_agent.run_sync.return_value = mock_result

    enricher = VisionEnricher()
    desc = enricher.generate_image_description(b"img")
    assert desc == "Desc"
    mock_agent.run_sync.assert_called_once()

    # Check args (optional but good)
    args = mock_agent.run_sync.call_args[0]
    assert len(args) == 1
    content_list = args[0]
    assert isinstance(content_list, list)
    assert content_list[0] == "Describe this image from an educational textbook in detail. Focus on the educational content, text, diagrams, and any visual cues relevant for a student. If there is text, transcribe it."
    assert isinstance(content_list[1], BinaryContent)
