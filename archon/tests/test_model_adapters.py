"""Tests for Model adapters: OpenAIAdapter, LiteLLMAdapter, MockModelAdapter, and StructuredOutputParser."""
import json
import pytest
from pydantic import BaseModel, Field
import httpx

from archon.core.step import StepResult
from archon.exceptions import (
    ModelAuthenticationError,
    ModelMaxRetriesExceededError,
    ModelResponseValidationError,
)
from archon.models import (
    BaseModelAdapter,
    LiteLLMAdapter,
    MockModelAdapter,
    OpenAIAdapter,
)
from archon.models.structured import StructuredOutputParser


class UserProfileSchema(BaseModel):
    user_id: int
    name: str
    roles: list[str] = Field(default_factory=list)


class TestStructuredOutputParser:
    """TDD tests for Pydantic v2 StructuredOutputParser."""

    def test_parse_valid_json_success(self):
        raw_json = json.dumps({"user_id": 42, "name": "Alice", "roles": ["admin"]})
        result = StructuredOutputParser.parse(raw_json, UserProfileSchema)

        assert isinstance(result, UserProfileSchema)
        assert result.user_id == 42
        assert result.name == "Alice"
        assert result.roles == ["admin"]

    def test_parse_markdown_wrapped_json_success(self):
        wrapped = """Here is the result:
```json
{
  "user_id": 101,
  "name": "Bob",
  "roles": ["developer", "reviewer"]
}
```
Hope this helps!"""
        result = StructuredOutputParser.parse(wrapped, UserProfileSchema)

        assert isinstance(result, UserProfileSchema)
        assert result.user_id == 101
        assert result.name == "Bob"

    def test_parse_invalid_json_raises_validation_error(self):
        non_json = "I cannot complete this request as JSON."
        with pytest.raises(ModelResponseValidationError) as exc_info:
            StructuredOutputParser.parse(non_json, UserProfileSchema)

        assert "JSON" in str(exc_info.value)
        assert exc_info.value.raw_response == non_json

    def test_parse_schema_mismatch_raises_validation_error(self):
        # Missing required field 'name'
        invalid_schema = json.dumps({"user_id": 1})
        with pytest.raises(ModelResponseValidationError) as exc_info:
            StructuredOutputParser.parse(invalid_schema, UserProfileSchema)

        assert exc_info.value.raw_response == invalid_schema
        assert exc_info.value.validation_errors is not None


class TestOpenAIAdapterMockTransport:
    """TDD tests for OpenAIAdapter using custom HTTPX MockTransport."""

    @pytest.mark.asyncio
    async def test_successful_chat_completion(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert payload["model"] == "gpt-4o"
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Hello from OpenAI!",
                                "tool_calls": [],
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)

        adapter = OpenAIAdapter(
            api_key="test-key",
            model_name="gpt-4o",
            http_client=client,
        )

        step = await adapter.async_generate([{"role": "user", "content": "Hi"}])

        assert isinstance(step, StepResult)
        assert step.text == "Hello from OpenAI!"
        assert step.is_complete is True
        assert step.metadata["prompt_tokens"] == 10

    @pytest.mark.asyncio
    async def test_authentication_error_fast_fails(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "Invalid API key"}})

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)

        adapter = OpenAIAdapter(
            api_key="bad-key",
            model_name="gpt-4o",
            http_client=client,
        )

        with pytest.raises(ModelAuthenticationError):
            await adapter.async_generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_streaming_generation(self):
        def handler(request: httpx.Request) -> httpx.Response:
            content = "data: {\"choices\": [{\"delta\": {\"content\": \"Hello \"}}]}\n\ndata: {\"choices\": [{\"delta\": {\"content\": \"world!\"}}]}\n\ndata: [DONE]\n\n"
            return httpx.Response(200, text=content, headers={"Content-Type": "text/event-stream"})

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)

        adapter = OpenAIAdapter(
            api_key="test-key",
            model_name="gpt-4o",
            http_client=client,
        )

        chunks = []
        async for chunk in adapter.stream_generate([{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world!"


class TestLiteLLMAdapter:
    """TDD tests for LiteLLMAdapter multi-provider normalization."""

    @pytest.mark.asyncio
    async def test_litellm_mock_routing(self):
        adapter = LiteLLMAdapter(model_name="anthropic/claude-3-5-sonnet")
        assert adapter.model_name == "anthropic/claude-3-5-sonnet"
        assert adapter.provider == "anthropic"

        # Offline fallback without credentials returns formatted mock step
        step = await adapter.async_generate([{"role": "user", "content": "Hello"}])
        assert isinstance(step, StepResult)
        assert step.is_complete is True
