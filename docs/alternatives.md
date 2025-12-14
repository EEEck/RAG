# Architecture Alternatives: LLM Abstraction

## 1. PydanticAI (Recommended)
**Status**: Partially implemented (`app/services/agent_service.py`).
**Concept**: Use `pydantic_ai.Agent` as the unified interface.
**Pros**:
- **Structured Output**: Native support for Pydantic models across providers (OpenAI, Gemini, Groq, etc.). Handles the complexity of translating Pydantic schemas to provider-specific formats (JSON mode, Tool calling).
- **VLM Support**: Native support for image inputs.
- **Unified Interface**: Same API for Chat, Vision, and Agents.
- **Already Installed**: No new dependencies.
- **Type Safety**: Strong typing throughout.

**Cons**:
- **Learning Curve**: Requires learning the `pydantic_ai` API.
- **Abstraction Leakage**: Sometimes you need to tweak the underlying model parameters (temp, top_p) which might require digging into the `Model` config.

## 2. Custom "Client Adapter" Pattern
**Status**: Not implemented.
**Concept**: Define a custom abstract base class `LLMClientPort` and implement adapters (`OpenAIAdapter`, `AnthropicAdapter`).
**Pros**:
- **Simplicity**: specific to our exact needs (e.g., `generate_quiz(request)`).
- **Control**: Full control over how requests are constructed.
- **No Magic**: You can see exactly what is sent to the API.

**Cons**:
- **Boilerplate**: We must manually implement "Pydantic -> JSON Schema" conversion for every provider.
- **Maintenance**: We must maintain adapters for every model we want to support (OpenAI, Anthropic, Gemini).
- **Duplication**: We would likely end up re-implementing logic that `pydantic.ai` already provides (like validation retries).

## Recommendation
Given that `pydantic.ai` is already a dependency and actively used in `AgentService`, adopting it fully is actually the **simplest** path in terms of code consistency and maintenance. A custom adapter would introduce a *second* pattern for LLM interaction.

We will proceed with **PydanticAI**, but wrapped in a **Factory** to ensure configuration simplicity.
