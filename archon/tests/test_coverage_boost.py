"""Coverage booster tests exercising edge branches and public helper methods."""
import asyncio
import io
import json
import zipfile
import pytest
from pathlib import Path
import httpx

from archon import create_session
from archon.core.bus import MessageBus
from archon.core.context import ExecutionContext
from archon.core.session import AgentSession
from archon.core.step import StepResult
from archon.exceptions import (
    MessageBusClosedError,
    SessionClosedError,
    ToolSecurityError,
)
from archon.harness import (
    DatabaseHarnessProvider,
    FileSystemHarnessProvider,
    HarnessManifest,
    InMemoryHarnessProvider,
)
from archon.models import (
    BaseModelAdapter,
    LiteLLMAdapter,
    MockModelAdapter,
    OpenAIAdapter,
)
from archon.models.structured import StructuredOutputParser
from archon.skills.definition import SkillDefinition
from archon.subagents.definition import SubagentDefinition, SubagentRequest
from archon.tools import BaseTool, ToolRegistry, tool


class TestCoverageBoost:
    """Tests targeting uncovered branches across all 6 modules."""

    def test_factory_variants(self, tmp_path):
        # 1. From HarnessManifest
        manifest = HarnessManifest(constitution="Constitution")
        sess1 = create_session(manifest)
        assert sess1.session_id.startswith("sess_")

        # 2. From Provider
        prov = FileSystemHarnessProvider(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# FS Const")
        sess2 = create_session(prov)
        assert "FS Const" in sess2.compile_system_prompt()

        # 3. From bytes
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("AGENTS.md", "# Zip Const")
        sess3 = create_session(zip_buf.getvalue(), model="gpt-4o")
        assert "Zip Const" in sess3.compile_system_prompt()

        # 4. From str
        sess4 = create_session(str(tmp_path), model=MockModelAdapter())
        assert "FS Const" in sess4.compile_system_prompt()

        # 5. Invalid type raises TypeError
        with pytest.raises(TypeError):
            create_session(12345)

    @pytest.mark.asyncio
    async def test_session_stream_and_sync_run(self, tmp_path):
        manifest = HarnessManifest(constitution="Constitution")
        model = MockModelAdapter(canned_responses=[
            StepResult(text="Stream output token", is_complete=True),
            StepResult(text="Sync run output", is_complete=True),
        ])
        session = AgentSession(
            session_id="sess-stream",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        # Stream test
        streamed = []
        async for chunk in session.stream("Tell me"):
            streamed.append(chunk)
        assert "".join(streamed) == "Stream output token"

        # Sync run test
        res = session.run("Run sync")
        assert res.text == "Sync run output"

        # Closed session on stream and invoke_subagents
        session.close()
        with pytest.raises(SessionClosedError):
            async for _ in session.stream("Hello"):
                pass

        with pytest.raises(SessionClosedError):
            await session.invoke_subagents([SubagentRequest(subagent_name="a", prompt="p")])

    def test_tool_registry_and_function_tool_types(self):
        registry = ToolRegistry()

        @tool
        def complex_tool(
            count: int,
            ratio: float,
            active: bool,
            items: list,
            options: dict,
            default_val: str = "default",
        ) -> str:
            """Tool with multiple parameter types."""
            return f"{count}-{ratio}-{active}-{len(items)}-{len(options)}-{default_val}"

        registry.register(complex_tool)
        assert len(registry) == 1
        assert "complex_tool" in list(iter(registry))

        # Direct invocation via __call__
        direct_out = complex_tool(1, 2.5, True, [1], {"k": "v"})
        assert direct_out == "1-2.5-True-1-1-default"

        # register_func test
        def plain_func(x: int) -> int:
            return x * 2

        wrapped = registry.register_func(plain_func, name="double", description="Double x")
        assert len(registry) == 2
        res = wrapped.execute(x=5)
        assert res.stdout == "10"

    def test_database_harness_provider_dict_format(self):
        records = {
            "constitution": "# DB Dict Format",
            "skills": {
                "skill_1": {"name": "skill_1", "description": "d1", "instructions": "i1"}
            },
            "subagents": {
                "agent_1": {
                    "name": "agent_1",
                    "description": "a1",
                    "system_prompt": "p1",
                    "allowed_tools": ["bash"],
                }
            },
        }
        provider = DatabaseHarnessProvider(records=records)
        manifest = provider.load()
        assert "skill_1" in manifest.skills
        assert "agent_1" in manifest.subagents

    @pytest.mark.asyncio
    async def test_message_bus_unsubscribe_and_timeout(self):
        bus = MessageBus()
        bus.register_recipient("agent_test")

        received = []
        def handler(payload):
            received.append(payload)

        bus.subscribe("EVT", handler)
        await bus.publish("EVT", "first")
        assert len(received) == 1

        bus.unsubscribe("EVT", handler)
        await bus.publish("EVT", "second")
        assert len(received) == 1  # Unsubscribed, no new message

        # receive_message timeout raises TimeoutError
        with pytest.raises(TimeoutError):
            await bus.receive_message("agent_test", timeout=0.01)

        bus.unregister_recipient("agent_test")
        with pytest.raises(Exception):
            await bus.receive_message("agent_test", timeout=0.01)

    def test_context_child_vars_merge(self):
        ctx = ExecutionContext(session_id="s1", variables={"base": "val"})
        child = ctx.create_child("worker", extra="extra_val")
        assert child.depth == 1
        assert child.variables["base"] == "val"
        assert child.variables["extra"] == "extra_val"

    @pytest.mark.asyncio
    async def test_openai_adapter_sync_generate_and_retry(self):
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 500 error triggers retry
                return httpx.Response(500, json={"error": "server error"})
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Success after retry",
                                "tool_calls": [
                                    {"function": {"name": "test_tool", "arguments": "{\"k\": 1}"}}
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 5},
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)
        adapter = OpenAIAdapter(api_key="key", http_client=client)

        step = adapter.generate([{"role": "user", "content": "hi"}])
        assert step.text == "Success after retry"
        assert len(step.tool_calls) == 1
        assert step.tool_calls[0]["arguments"] == {"k": 1}

    @pytest.mark.asyncio
    async def test_litellm_adapter_sync_and_stream(self):
        adapter = LiteLLMAdapter(model_name="openai/gpt-3.5-turbo")
        step = adapter.generate([{"role": "user", "content": "Test prompt"}])
        assert "Test prompt" in step.text

        streamed = []
        async for chunk in adapter.stream_generate([{"role": "user", "content": "Stream test"}]):
            streamed.append(chunk)
        assert len(streamed) == 1

    def test_strict_json_schema(self):
        from pydantic import BaseModel

        class StrictModel(BaseModel):
            id: int
            name: str

        schema = StructuredOutputParser.get_strict_json_schema(StrictModel)
        assert schema["additionalProperties"] is False
        assert "id" in schema["properties"]
        assert "name" in schema["properties"]
