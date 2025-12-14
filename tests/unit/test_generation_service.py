import pytest
from unittest.mock import MagicMock, patch
from app.services.generation import generate_items, PromptFactory
from app.schemas import GenerateItemsRequest, ConceptPack, GeneratedItem, PedagogyConfig

@patch("app.services.generation.create_agent")
def test_generate_items(mock_create_agent):
    req = GenerateItemsRequest(
        textbook_id="b1",
        lesson_code="L1",
        concept_pack=ConceptPack(vocab=["apple"]),
        count=1
    )

    mock_agent = MagicMock()
    mock_result = MagicMock()

    # Use real model instance
    item = GeneratedItem(stem="Question?", options=["A"], answer="A")

    # Mock GeneratedItemList structure
    mock_result.data.items = [item]

    mock_agent.run_sync.return_value = mock_result
    mock_create_agent.return_value = mock_agent

    resp = generate_items(req)

    assert len(resp.items) == 1
    assert resp.items[0].stem == "Question?"
    mock_agent.run_sync.assert_called_once()

def test_prompt_factory():
    # Just testing the class logic
    prompt = PromptFactory.get_prompt("language")
    assert "ESL" in prompt

    config = PedagogyConfig(tone="humorous")
    prompt = PromptFactory.get_prompt("language", config)
    assert "Tone: humorous" in prompt
