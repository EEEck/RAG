import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from ingest.openai_ingestor import OpenAIIngestor

@patch("ingest.openai_ingestor.AsyncOpenAI")
def test_openai_ingestor_init(mock_openai):
    ingestor = OpenAIIngestor("key")
    assert ingestor is not None
    mock_openai.assert_called_once()

@pytest.mark.asyncio
@patch("ingest.openai_ingestor.AsyncOpenAI")
@patch("ingest.openai_ingestor.fitz.open")
async def test_ingest_book_async(mock_fitz_open, mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    # Mock doc
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc

    # Mock page conversion
    mock_page = MagicMock()
    mock_page.get_pixmap.return_value.tobytes.return_value = b"image"
    mock_doc.load_page.return_value = mock_page

    ingestor = OpenAIIngestor("key")

    # Mock process_page to avoid actual API call structure which is complex
    # Or mock client.beta.chat.completions.parse

    mock_parsed_response = MagicMock()
    mock_parsed_response.atoms = []
    mock_parsed_response.unit_number = 1

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.parsed = mock_parsed_response

    mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

    results = await ingestor.ingest_book("test.pdf", category="language")
    assert len(results) == 1
    assert results[0]['status'] == "success"
