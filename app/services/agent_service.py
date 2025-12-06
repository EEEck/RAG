from __future__ import annotations

import os
from typing import List, Optional, Union, Any, Dict
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart, TextPart, ModelResponse
from app.schemas import (
    AgentChatResponse,
    AgentMessage,
    QuizPlan,
    SearchPlan,
    Clarification,
    AgentOutput,
    ExecutePlanRequest
)
from app.celery_worker import generate_quiz_task
from app.services.search_service import get_search_service
from app.services.profile_service import get_profile_service
from app.services.books_service import get_book_service

# Define the PydanticAI Agent
# We use a Union return type so the agent can either Plan or Ask.
agent = Agent(
    'openai:gpt-4o',
    deps_type=Optional[str],  # profile_id
    output_type=AgentOutput,
    system_prompt=(
        "You are a helpful Teaching Assistant Agent. Your goal is to help teachers create lesson plans, quizzes, and find content.\n"
        "You DO NOT execute the actions yourself. Instead, you create a PLAN for the action.\n"
        "If you do not have enough information to create a valid plan (e.g. missing book_id or unit), return a Clarification object.\n"
        "If you have enough info, return a QuizPlan or SearchPlan object."
    )
)

@agent.tool
def list_books(ctx: RunContext[Optional[str]]) -> str:
    """
    Lists the books available to the teacher based on their profile.
    Use this to verify book IDs or find available books.
    """
    profile_id = ctx.deps
    if not profile_id:
        return "No profile context available."

    try:
        profile_service = get_profile_service()
        profile = profile_service.get_profile(profile_id)
        if not profile or not profile.book_list:
            return "No books found in profile."

        book_service = get_book_service()
        summaries = []
        for bid in profile.book_list:
            book = book_service.get_book(bid)
            if book:
                summaries.append(f"ID: {bid}, Title: {book.title}")
            else:
                summaries.append(f"ID: {bid}")
        return "\n".join(summaries)
    except Exception as e:
        return f"Error fetching books: {str(e)}"

class AgentService:
    def plan_action(self, messages: List[AgentMessage], profile_id: Optional[str] = None) -> AgentChatResponse:
        """
        Uses PydanticAI to process the conversation and return a plan or clarification.
        """
        if not messages:
             return AgentChatResponse(status="incomplete", message="Hello! How can I help you?")

        # Convert app.schemas.AgentMessage to PydanticAI ModelMessage list
        # We separate the *last* message as the current prompt, and the rest as history.
        current_msg_content = messages[-1].content
        history_msgs = messages[:-1]

        pydantic_history: List[ModelMessage] = []

        for msg in history_msgs:
            if msg.role == "user":
                pydantic_history.append(
                    ModelRequest(parts=[UserPromptPart(content=msg.content)])
                )
            elif msg.role == "assistant":
                # For assistant, PydanticAI expects ModelResponse.
                pydantic_history.append(
                    ModelResponse(parts=[TextPart(content=msg.content)])
                )
            # We skip 'system' as it is handled by the agent's system_prompt definition

        try:
            # We pass profile_id as dependency
            result = agent.run_sync(
                current_msg_content,
                deps=profile_id,
                message_history=pydantic_history
            )
            output = result.data

            if isinstance(output, Clarification):
                return AgentChatResponse(
                    status="incomplete",
                    message=output.question,
                    plan=None
                )
            elif isinstance(output, (QuizPlan, SearchPlan)):
                return AgentChatResponse(
                    status="ready",
                    message=f"I've created a plan: {output.description}",
                    plan=output
                )
            else:
                # Should not be reachable if type safety works, but good fallback
                return AgentChatResponse(status="incomplete", message="I'm not sure what to do.")

        except Exception as e:
            print(f"Agent Error: {e}")
            return AgentChatResponse(status="incomplete", message="Sorry, I encountered an error processing your request.")

    def execute_plan(self, request: ExecutePlanRequest) -> Dict[str, Any]:
        """
        Executes a confirmed plan.
        """
        plan = request.plan

        # Security Check: Verify book_id ownership if profile_id provided
        if request.profile_id and plan.book_id:
            try:
                profile_service = get_profile_service()
                profile = profile_service.get_profile(request.profile_id)

                # If profile exists, check if book_id is in its list
                # If profile has no books, we assume strict mode might block it,
                # but here we just check if book is accessible.
                # If plan.book_id is NOT in profile.book_list, we should block.
                # NOTE: If user searches Global content (no book_id), that's fine.
                # But if they specify a book_id, it must be theirs (if they have a profile context).

                if profile and profile.book_list:
                     if plan.book_id not in profile.book_list:
                         return {"status": "error", "message": f"Access denied. Book {plan.book_id} is not in your profile."}
            except Exception as e:
                print(f"Security Check Error: {e}")
                # Fail safe? Or allow? Safer to fail.
                return {"status": "error", "message": "Security validation failed."}

        if isinstance(plan, QuizPlan):
            import uuid
            user_job_id = str(uuid.uuid4())
            task = generate_quiz_task.delay(user_job_id, plan.book_id, plan.unit, plan.topic)
            return {
                "status": "success",
                "message": "Quiz generation started.",
                "job_id": task.id,
                "result_url": f"/jobs/{task.id}"
            }

        elif isinstance(plan, SearchPlan):
            search_service = get_search_service()
            book_ids = [plan.book_id] if plan.book_id else None

            response = search_service.search_content(
                query=plan.query,
                limit=5,
                max_unit=plan.unit, # Mapping unit to max_unit/curriculum guard
                book_ids=book_ids,
                user_id=None
            )
            return {
                "status": "success",
                "data": response.dict()
            }

        else:
             return {"status": "error", "message": "Unknown plan type."}

def get_agent_service() -> AgentService:
    return AgentService()
