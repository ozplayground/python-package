"""Tests for SubagentRunner, invoke_subagents top-level helper, and deep cycle governance."""
import asyncio
import pytest

from archon.core.context import ExecutionContext
from archon.core.step import StepResult
from archon.exceptions import (
    SubagentCycleDetectedError,
    SubagentDepthExceededError,
)
from archon.harness.manifest import HarnessManifest
from archon.models.mock import MockModelAdapter
from archon.skills.definition import SkillDefinition
from archon.subagents import (
    SubagentDefinition,
    SubagentRequest,
    SubagentResult,
    SubagentRunner,
    invoke_subagents,
)


class MockRunnerSession:
    def __init__(self, manifest: HarnessManifest, model_adapter=None):
        self.manifest = manifest
        self.model_adapter = model_adapter or MockModelAdapter()
        from archon.core.bus import MessageBus
        self.message_bus = MessageBus()
        from archon.skills.registry import SkillRegistry
        self.skill_registry = SkillRegistry(manifest.skills)


class TestSubagentRunnerAndHelpers:
    """TDD tests for SubagentRunner and invoke_subagents."""

    @pytest.mark.asyncio
    async def test_subagent_runner_success_with_injected_skills(self):
        subagent_def = SubagentDefinition(
            name="tester",
            description="Tester Subagent",
            system_prompt="You are a test expert.",
            required_skills=["pytest_skill"],
        )
        skills = {
            "pytest_skill": SkillDefinition(
                name="pytest_skill",
                instructions="Use fixtures effectively.",
            )
        }
        manifest = HarnessManifest(constitution="Constitution", skills=skills, subagents={"tester": subagent_def})
        model = MockModelAdapter(canned_responses=[StepResult(text="Test completed 100%", is_complete=True)])
        session = MockRunnerSession(manifest, model)

        runner = SubagentRunner(session=session)
        request = SubagentRequest(subagent_name="tester", prompt="Run suite")
        context = ExecutionContext(session_id="sess-runner")

        result = await runner.run(subagent_def, request, context)

        assert isinstance(result, SubagentResult)
        assert result.is_success is True
        assert result.subagent_name == "tester"
        assert result.output == "Test completed 100%"
        assert result.is_timeout is False

        # Verify that pytest_skill was injected into system prompt
        called_messages = model.calls[0]["messages"]
        system_content = next(m["content"] for m in called_messages if m["role"] == "system")
        assert "Use fixtures effectively." in system_content

    @pytest.mark.asyncio
    async def test_subagent_runner_timeout_marks_is_timeout(self):
        subagent_def = SubagentDefinition(
            name="sleeper",
            description="Slow subagent",
            system_prompt="Slow",
            timeout_seconds=0.1,  # 100ms timeout
        )
        manifest = HarnessManifest(constitution="Constitution", subagents={"sleeper": subagent_def})

        class HangingModel(MockModelAdapter):
            async def async_generate(self, messages, tools=None):
                await asyncio.sleep(0.5)
                return StepResult(text="done", is_complete=True)

        session = MockRunnerSession(manifest, HangingModel())
        runner = SubagentRunner(session=session)
        request = SubagentRequest(subagent_name="sleeper", prompt="sleep now", timeout_seconds=0.1)
        context = ExecutionContext(session_id="sess-timeout")

        result = await runner.run(subagent_def, request, context)

        assert result.is_success is False
        assert result.is_timeout is True
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_subagents_standalone_helper(self):
        subagents = {
            "agent_1": SubagentDefinition(name="agent_1", system_prompt="agent 1 prompt"),
            "agent_2": SubagentDefinition(name="agent_2", system_prompt="agent 2 prompt"),
        }
        manifest = HarnessManifest(constitution="Constitution", subagents=subagents)
        model = MockModelAdapter(canned_responses=[
            StepResult(text="response 1", is_complete=True),
            StepResult(text="response 2", is_complete=True),
        ])
        session = MockRunnerSession(manifest, model)

        requests = [
            SubagentRequest(subagent_name="agent_1", prompt="Task 1"),
            SubagentRequest(subagent_name="agent_2", prompt="Task 2"),
        ]

        results = await invoke_subagents(session, requests)

        assert len(results) == 2
        assert results[0].is_success is True
        assert results[0].output == "response 1"
        assert results[1].is_success is True
        assert results[1].output == "response 2"

    @pytest.mark.asyncio
    async def test_multi_hop_cycle_detection(self):
        """Lineage A -> B -> C attempting to call A must fail with cycle detection."""
        subagents = {
            "agent_a": SubagentDefinition(name="agent_a"),
            "agent_b": SubagentDefinition(name="agent_b"),
            "agent_c": SubagentDefinition(name="agent_c"),
        }
        manifest = HarnessManifest(constitution="Constitution", subagents=subagents)
        session = MockRunnerSession(manifest)

        requests = [SubagentRequest(subagent_name="agent_a", prompt="Loop back")]
        context = ExecutionContext(
            session_id="sess-cycle",
            depth=2,
            caller_lineage=("agent_a", "agent_b", "agent_c"),
        )

        with pytest.raises(SubagentCycleDetectedError) as exc_info:
            await invoke_subagents(session, requests, context=context)

        assert "agent_a" in str(exc_info.value)
