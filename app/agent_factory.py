from typing import Optional, Type, Any, Union
from pydantic_ai import Agent
from app.config import get_settings

def create_agent(
    result_type: Optional[Type[Any]] = None,
    system_prompt: str = "",
    deps_type: Type[Any] = Any,
    model_override: Optional[str] = None,
) -> Agent:
    settings = get_settings()
    model = model_override or settings.llm_model

    return Agent(
        model,
        output_type=result_type,
        system_prompt=system_prompt,
        deps_type=deps_type,
    )
