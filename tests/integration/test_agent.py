import pytest
from unittest.mock import MagicMock, patch
from app.services.agent_service import AgentService
from app.schemas import AgentMessage, QuizPlan, Clarification, ExecutePlanRequest, SearchPlan

# Mocking PydanticAI Agent run_sync is tricky because it returns a specific RunResult.
# We will mock the `agent.run_sync` method on the imported object.

@patch("app.services.agent_service.agent")
def test_plan_action_incomplete(mock_agent):
    service = AgentService()

    # Mock result for Clarification
    mock_result = MagicMock()
    mock_result.data = Clarification(question="Which unit?")
    mock_agent.run_sync.return_value = mock_result

    messages = [AgentMessage(role="user", content="Make a quiz")]
    response = service.plan_action(messages)

    assert response.status == "incomplete"
    assert response.message == "Which unit?"
    assert response.plan is None

@patch("app.services.agent_service.agent")
def test_plan_action_ready(mock_agent):
    service = AgentService()

    # Mock result for QuizPlan
    plan = QuizPlan(book_id="123", unit=1, topic="Verbs", description="Quiz on Verbs")
    mock_result = MagicMock()
    mock_result.data = plan
    mock_agent.run_sync.return_value = mock_result

    messages = [AgentMessage(role="user", content="Make a quiz for Unit 1")]
    response = service.plan_action(messages)

    assert response.status == "ready"
    assert isinstance(response.plan, QuizPlan)
    assert response.plan.topic == "Verbs"

@patch("app.services.agent_service.generate_quiz_task")
def test_execute_plan_quiz(mock_task):
    service = AgentService()
    mock_task.delay.return_value.id = "job-123"

    plan = QuizPlan(book_id="b1", unit=2, topic="Nature", description="Test Quiz")
    req = ExecutePlanRequest(plan=plan)

    result = service.execute_plan(req)

    assert result["status"] == "success"
    assert result["job_id"] == "job-123"
    mock_task.delay.assert_called_once()

@patch("app.services.agent_service.get_search_service")
def test_execute_plan_search(mock_get_service):
    service = AgentService()

    mock_search = MagicMock()
    mock_search.search_content.return_value.dict.return_value = {"atoms": []}
    mock_get_service.return_value = mock_search

    plan = SearchPlan(query="hello", book_id="b1", description="Search hello")
    req = ExecutePlanRequest(plan=plan)

    result = service.execute_plan(req)

    assert result["status"] == "success"
    mock_search.search_content.assert_called_once()
