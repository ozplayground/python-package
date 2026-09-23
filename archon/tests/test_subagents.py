"""Tests for Subagent orchestration, parallel dispatch, semaphore limit, and cycle detection."""
import asyncio
import pytest
from unittest.mock import MagicMock

from archon.exceptions import (
    SubagentCycleDetectedError,
    SubagentDepthExceededError,
    SubagentNotFoundError,
)
from archon.harness.manifest import HarnessManifest
from archon.skills.definition import SkillDefinition
from archon.subagents import (
    MessageBus,
    SubagentDefinition,
    SubagentDispatcher,
    SubagentRequest,
    SubagentResult,
)


class DummySession:
    """Mock session for testing dispatcher without full LLM integration."""

    def __init__(self, manifest: HarnessManifest):
        self.manifest = manifest
        self.message_bus = MessageBus()

    async def execute_subagent_run(self, subagent_def, request, child_context):
        # Emulate work
        await asyncio.sleep(0.01)
        if "fail" in request.prompt:
            raise RuntimeError("Subagent execution failed intentionally")
        return f"Output from {subagent_def.name}: {request.prompt}"


def create_test_manifest() -> HarnessManifest:
    subagents = {
        "backend": SubagentDefinition(
            name="backend",
            description="Backend Engineer",
            required_skills=["python"],
        ),
        "frontend": SubagentDefinition(
            name="frontend",
            description="Frontend Engineer",
        ),
        "nested": SubagentDefinition(
            name="nested",
            description="Nested Worker",
        ),
    }
    skills = {
        "python": SkillDefinition(name="python", instructions="Write type hints."),
    }
    return HarnessManifest(
        constitution="Test Constitution",
        subagents=subagents,
        skills=skills,
    )


class TestMessageBus:
    """Tests for MessageBus pub/sub."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        bus = MessageBus()
        received = []

        def sync_handler(payload):
            received.append(f"sync:{payload}")

        async def async_handler(payload):
            received.append(f"async:{payload}")

        bus.subscribe("TEST_EVENT", sync_handler)
        bus.subscribe("TEST_EVENT", async_handler)

        await bus.publish("TEST_EVENT", "hello")

        assert len(received) == 2
        assert "sync:hello" in received
        assert "async:hello" in received


class TestSubagentDispatcher:
    """Tests for SubagentDispatcher parallel execution and governance policies."""

    @pytest.mark.asyncio
    async def test_parallel_dispatch_success(self):
        session = DummySession(create_test_manifest())
        dispatcher = SubagentDispatcher(concurrency_limit=5)

        requests = [
            SubagentRequest(subagent_name="backend", prompt="Design user API"),
            SubagentRequest(subagent_name="frontend", prompt="Build login page"),
        ]

        from archon.core.context import ExecutionContext

        root_ctx = ExecutionContext(session_id="sess-1")
        results = await dispatcher.dispatch(session, requests, root_ctx)

        assert len(results) == 2
        assert results[0].is_success is True
        assert results[0].subagent_name == "backend"
        assert "Output from backend" in results[0].output

        assert results[1].is_success is True
        assert results[1].subagent_name == "frontend"
        assert "Output from frontend" in results[1].output

    @pytest.mark.asyncio
    async def test_subagent_not_found_raises_error(self):
        session = DummySession(create_test_manifest())
        dispatcher = SubagentDispatcher()

        from archon.core.context import ExecutionContext

        root_ctx = ExecutionContext(session_id="sess-1")
        requests = [SubagentRequest(subagent_name="nonexistent", prompt="Do something")]

        with pytest.raises(SubagentNotFoundError):
            await dispatcher.dispatch(session, requests, root_ctx)

    @pytest.mark.asyncio
    async def test_max_depth_exceeded_raises_error(self):
        session = DummySession(create_test_manifest())
        dispatcher = SubagentDispatcher()

        from archon.core.context import ExecutionContext

        # Context already at depth 3
        deep_ctx = ExecutionContext(
            session_id="sess-1",
            depth=3,
            caller_lineage=("main", "sub1", "sub2", "sub3"),
        )
        requests = [SubagentRequest(subagent_name="nested", prompt="Too deep")]

        with pytest.raises(SubagentDepthExceededError):
            await dispatcher.dispatch(session, requests, deep_ctx)

    @pytest.mark.asyncio
    async def test_circular_lineage_detected_raises_error(self):
        session = DummySession(create_test_manifest())
        dispatcher = SubagentDispatcher()

        from archon.core.context import ExecutionContext

        # Calling 'backend' when 'backend' is already an ancestor in lineage
        cyclic_ctx = ExecutionContext(
            session_id="sess-1",
            depth=2,
            caller_lineage=("main", "backend", "nested"),
        )
        requests = [SubagentRequest(subagent_name="backend", prompt="Recursive loop")]

        with pytest.raises(SubagentCycleDetectedError) as exc_info:
            await dispatcher.dispatch(session, requests, cyclic_ctx)

        assert "backend" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_partial_failure_fault_tolerance(self):
        """Verify when 1 subagent fails, other successful results are preserved."""
        session = DummySession(create_test_manifest())
        dispatcher = SubagentDispatcher()

        from archon.core.context import ExecutionContext

        root_ctx = ExecutionContext(session_id="sess-1")
        requests = [
            SubagentRequest(subagent_name="backend", prompt="Good task"),
            SubagentRequest(subagent_name="frontend", prompt="fail task"),
        ]

        results = await dispatcher.dispatch(session, requests, root_ctx)

        assert len(results) == 2
        # First succeeded
        assert results[0].subagent_name == "backend"
        assert results[0].is_success is True

        # Second failed gracefully without crashing the whole dispatch
        assert results[1].subagent_name == "frontend"
        assert results[1].is_success is False
        assert "failed intentionally" in results[1].error
