from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Depends

from ..schemas import AgentChatRequest, AgentChatResponse, ExecutePlanRequest
from ..services.agent_service import get_agent_service, AgentService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def chat(req: AgentChatRequest) -> AgentChatResponse:
    """
    Analyzes the conversation history and user intent using PydanticAI.
    Returns a status ('incomplete' or 'ready') and optionally a plan.
    """
    service: AgentService = get_agent_service()
    try:
        response = service.plan_action(req.messages, req.profile_id)
        return response
    except Exception as e:
        # Log the error for debugging
        print(f"Chat Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=Dict[str, Any])
def execute_plan(req: ExecutePlanRequest) -> Dict[str, Any]:
    """
    Executes a confirmed plan.
    """
    service: AgentService = get_agent_service()
    try:
        result = service.execute_plan(req)
        return result
    except Exception as e:
        print(f"Execute Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
