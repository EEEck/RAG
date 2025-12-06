import pytest
from unittest.mock import MagicMock, patch
from app.services.generation import generate_items, PromptFactory
from app.schemas import GenerateItemsRequest, ConceptPack, PedagogyConfig

@patch("app.services.generation.get_sync_client")
def test_generate_items(mock_get_client):
    # Mock LLM response
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock completion
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
        "items": [
            {"stem": "Question?", "answer": "Answer"}
        ],
        "scope_report": {"violations": 0}
    }
    """
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    req = GenerateItemsRequest(
        textbook_id="b1",
        lesson_code="1.1",
        concept_pack=ConceptPack(vocab=["a"]),
        category="language"
    )

    resp = generate_items(req)
    assert len(resp.items) == 1
    assert resp.items[0].stem == "Question?"

def test_prompt_factory():
    # Just testing the class logic
    prompt = PromptFactory.get_prompt("language")
    assert "ESL" in prompt

    config = PedagogyConfig(tone="humorous")
    prompt = PromptFactory.get_prompt("language", config)
    assert "Tone: humorous" in prompt
