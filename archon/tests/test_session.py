"""Tests for AgentSession, turn execution, tool invocation loops, and mock adapter."""
import asyncio
from pathlib import Path
import pytest

from archon.core.context import ExecutionContext
from archon.core.session import AgentSession
from archon.core.step import StepResult
from archon.exceptions import SessionClosedError
from archon.harness.manifest import HarnessManifest
from archon.models import MockModelAdapter
from archon.skills import SkillDefinition
from archon.subagents import SubagentDefinition, SubagentRequest
from archon.tools import BaseTool, ToolExecutionResult, ToolRegistry, tool


class TestAgentSession:
    """Tests for AgentSession lifecycle and execution loop."""

    def test_session_init_compiles_system_prompt(self, tmp_path):
        manifest = HarnessManifest(
            constitution="# Base Constitution\nRule 1: Be reliable.",
            rules={"style.md": "Use clean code."},
            skills={"tdd": SkillDefinition(name="tdd", instructions="Write tests first.")},
        )
        model = MockModelAdapter()
        session = AgentSession(
            session_id="sess-001",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        prompt = session.compile_system_prompt()
        assert "Base Constitution" in prompt
        assert "Rule 1: Be reliable." in prompt
        assert "Use clean code." in prompt

    @pytest.mark.asyncio
    async def test_session_async_run_simple_response(self, tmp_path):
        manifest = HarnessManifest(constitution="Constitution")
        mock_response = StepResult(text="I am ready to help.", is_complete=True)
        model = MockModelAdapter(canned_responses=[mock_response])

        session = AgentSession(
            session_id="sess-002",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        result = await session.async_run("Hello agent")
        assert result.text == "I am ready to help."
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_session_async_run_tool_call_loop(self, tmp_path):
        """Verify model returning a tool call results in tool execution and loop feedback."""
        manifest = HarnessManifest(constitution="Constitution")

        # Step 1: Model requests tool call
        tool_call_step = StepResult(
            text="Let me calculate this.",
            tool_calls=[{"name": "add", "arguments": {"a": 10, "b": 25}}],
            is_complete=False,
        )
        # Step 2: After receiving tool output, model completes
        final_step = StepResult(
            text="The sum is 35.",
            is_complete=True,
        )

        model = MockModelAdapter(canned_responses=[tool_call_step, final_step])
        session = AgentSession(
            session_id="sess-003",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        @tool(name="add")
        def add(a: int, b: int) -> int:
            return a + b

        session.tool_registry.register(add)

        result = await session.async_run("Add 10 and 25")
        assert result.text == "The sum is 35."
        assert result.is_complete is True

    def test_session_closed_raises_session_closed_error(self, tmp_path):
        manifest = HarnessManifest(constitution="Constitution")
        model = MockModelAdapter(canned_responses=[StepResult(text="hi", is_complete=True)])
        session = AgentSession(
            session_id="sess-004",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        session.close()
        assert session.is_closed is True

        with pytest.raises(SessionClosedError):
            session.run("Any task")

    @pytest.mark.asyncio
    async def test_session_subagent_dispatch_integration(self, tmp_path):
        subagents = {
            "worker": SubagentDefinition(
                name="worker",
                description="Worker Subagent",
                system_prompt="You are a worker",
            )
        }
        manifest = HarnessManifest(constitution="Constitution", subagents=subagents)

        # Main agent calls subagent
        model = MockModelAdapter(
            canned_responses=[
                StepResult(text="Worker output summary", is_complete=True),  # subagent run
            ]
        )
        session = AgentSession(
            session_id="sess-005",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        results = await session.invoke_subagents(
            [SubagentRequest(subagent_name="worker", prompt="Do subtask")]
        )

        assert len(results) == 1
        assert results[0].is_success is True
        assert results[0].subagent_name == "worker"
        assert "Worker output summary" in results[0].output

    @pytest.mark.asyncio
    async def test_session_timeout_raises_error(self, tmp_path):
        from archon.exceptions import SessionTimeoutError

        manifest = HarnessManifest(constitution="Constitution")

        class SlowModel(MockModelAdapter):
            async def async_generate(self, messages, tools=None):
                await asyncio.sleep(0.5)
                return StepResult(text="late", is_complete=True)

        session = AgentSession(
            session_id="sess-timeout",
            manifest=manifest,
            model_adapter=SlowModel(),
            working_directory=tmp_path,
            session_timeout=0.1,  # 100ms timeout
        )

        with pytest.raises(SessionTimeoutError):
            await session.async_run("Quick task")

    def test_session_isolation_between_sessions(self, tmp_path):
        manifest = HarnessManifest(constitution="Constitution")
        model = MockModelAdapter()

        session_1 = AgentSession(
            session_id="sess-iso-1",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )
        session_2 = AgentSession(
            session_id="sess-iso-2",
            manifest=manifest,
            model_adapter=model,
            working_directory=tmp_path,
        )

        @tool(name="custom_tool_1")
        def tool_1() -> str:
            return "one"

        session_1.tool_registry.register(tool_1)

        assert "custom_tool_1" in session_1.tool_registry
        assert "custom_tool_1" not in session_2.tool_registry
        assert session_1.session_id != session_2.session_id
