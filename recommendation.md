# Recommendation: Refactoring to PydanticAI

## Executive Summary
We recommend refactoring the codebase to use **PydanticAI** for all Generative AI tasks (Text Generation, Vision/VLM, and Agents). This refactor is **highly feasible** and offers significant benefits in terms of type safety, model agnosticism, and maintainability.

The project already successfully utilizes PydanticAI in `app/services/agent_service.py`. Expanding this pattern to the rest of the application will standardize LLM interactions and allow for easier switching between providers (e.g., OpenAI, Gemini, Anthropic) via centralized configuration.

**Note:** This recommendation specifically covers Chat and Generation models. Embedding models (currently used in LlamaIndex and Memory Service) are **out of scope** for this refactor and will continue to use the existing OpenAI implementation for now.

## Feasibility Analysis

### 1. Text Generation (`app/services/generation.py`)
- **Current State:** Uses `openai.chat.completions.create` with `response_format={"type": "json_object"}` and manual JSON parsing.
- **PydanticAI Fit:** **Perfect**. PydanticAI natively supports structured outputs (returning Pydantic models), which will replace the manual JSON parsing and validation logic, reducing boilerplate and error potential.
- **Complexity:** Low. The `PromptFactory` logic can remain largely unchanged, while the execution logic is simplified.

### 2. VLM / Ingestion (`ingest/openai_ingestor.py`)
- **Current State:** Uses `client.beta.chat.completions.parse` with a dynamically created Pydantic model (`PageModel`) and base64 encoded images.
- **PydanticAI Fit:** **High**. PydanticAI supports `result_type` which accepts dynamic Pydantic models (classes). It also fully supports image inputs via `BinaryContent` or `ImageUrl` types, ensuring full VLM compatibility.
- **Complexity:** Medium. Requires mapping the existing PDF-to-Image logic to PydanticAI's message format, but the core logic remains the same.

### 3. Vision Enrichment (`ingest/vision_enricher.py`)
- **Current State:** Uses `client.chat.completions.create` with image URLs to generate text descriptions.
- **PydanticAI Fit:** **High**. Can be replaced by a simple Agent with a system prompt and image input.
- **Complexity:** Low.

## Proposed Architecture

### Centralized Configuration
To enable easy model switching, we will introduce a centralized configuration strategy in `app/config.py`. This avoids hardcoding model strings (like `'openai:gpt-4o'`) in the service files.

```python
# app/config.py (Conceptual)
class Settings(BaseSettings):
    # ... existing settings ...

    # Model Configuration
    # Syntax: provider:model_name (e.g., 'openai:gpt-4o', 'gemini:gemini-1.5-pro')
    llm_model: str = "openai:gpt-4o"
    vlm_model: str = "openai:gpt-4o"  # Separate config for Vision tasks if needed for specialized models
```

### Agent Factory
Instead of instantiating `Agent` classes directly with hardcoded strings, we will use a factory or utility function. This allows us to inject the configured model string dynamically.

```python
# app/agent_utils.py (Conceptual)
from app.config import get_settings

def create_agent(
    result_type: Type[T] | None = None,
    system_prompt: str = ...,
    model_override: str | None = None
) -> Agent[T]:
    settings = get_settings()
    model = model_override or settings.llm_model
    return Agent(model, result_type=result_type, system_prompt=system_prompt)
```

## Implementation Plan

### Phase 1: Infrastructure
1.  **Update `app/config.py`**: Add `LLM_MODEL` and `VLM_MODEL` environment variables/settings.
2.  **Create `app/agent_utils.py`**: Implement the factory function to centralize Agent creation and configuration.

### Phase 2: Refactor Generation (`app/services/generation.py`)
1.  Define the output schema (`GenerateItemsResponse`) as the `result_type` for the Agent.
2.  Replace `get_sync_client()` and `chat.completions.create` with `agent.run_sync()`.
3.  Remove manual JSON parsing and `json.loads` logic.

### Phase 3: Refactor Ingestion (`ingest/openai_ingestor.py`)
1.  Update `ingest_book` to instantiate a PydanticAI Agent instead of `AsyncOpenAI` client.
2.  Pass the dynamically created `PageModel` to the `result_type` argument.
3.  Convert the base64 image data to PydanticAI's `BinaryContent` format for the user prompt.

### Phase 4: Refactor Enrichment (`ingest/vision_enricher.py`)
1.  Replace the direct `OpenAI` client with a PydanticAI Agent.
2.  Use `settings.vlm_model` to configure the agent.
3.  Use PydanticAI's image handling for the input.

### Phase 5: Cleanup
1.  **Deprecate `app/openai_client.py`**: Once all services are migrated, this wrapper is no longer needed.
2.  **Update Tests**: Refactor `tests/test_openai_client.py` and integration tests to mock PydanticAI agents instead of low-level OpenAI clients.

## Files Affected
- `app/config.py`
- `app/services/generation.py`
- `ingest/openai_ingestor.py`
- `ingest/vision_enricher.py`
- `app/openai_client.py` (Target for removal)
- `tests/test_openai_client.py` (Refactor/Remove)
- `tests/integration/test_ingestion_gen.py` (Update mocking strategy)

## Conclusion
Refactoring to PydanticAI aligns with the project's goal of modularity and maintainability. It decouples the business logic from the specific OpenAI API implementation, allowing for future adoption of other models (e.g., Google Gemini, Anthropic Claude) with minimal code changes, while enforcing stricter type safety across the application.
