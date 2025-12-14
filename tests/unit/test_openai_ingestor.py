import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from ingest.openai_ingestor import OpenAIIngestor
from pydantic_ai import BinaryContent

@pytest.mark.asyncio
async def test_process_page():
    ingestor = OpenAIIngestor(api_key="fake")
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock() # run is async

    mock_result = MagicMock()
    mock_result.data = MagicMock(unit_number=1, lesson_title="Lesson 1", atoms=[])
    mock_agent.run.return_value = mock_result

    res = await ingestor.process_page(mock_agent, 0, b"img", "prompt")

    assert res["status"] == "success"
    mock_agent.run.assert_called_once()
    args = mock_agent.run.call_args[0]
    assert len(args) == 1
    content = args[0]
    assert isinstance(content, list)
    assert isinstance(content[1], BinaryContent)

@pytest.mark.asyncio
@patch("ingest.openai_ingestor.create_agent")
async def test_ingest_book(mock_create_agent):
    ingestor = OpenAIIngestor(api_key="fake")

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock()
    mock_result = MagicMock()
    mock_result.data = MagicMock(unit_number=1, lesson_title="Lesson 1", atoms=[])
    mock_agent.run.return_value = mock_result

    mock_create_agent.return_value = mock_agent

    # Mock fitz
    with patch("ingest.openai_ingestor.fitz") as mock_fitz:
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value.tobytes.return_value = b"fake_img"
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        results = await ingestor.ingest_book("dummy.pdf", category="language")

        assert len(results) == 1
        assert results[0]["status"] == "success"
        mock_create_agent.assert_called_once()
