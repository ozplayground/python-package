"""High-concurrency and load stress verification: 100 coroutines concurrent sessions and subagents."""
import asyncio
import pytest

from archon.core.context import ExecutionContext
from archon.core.session import AgentSession
from archon.core.step import StepResult
from archon.harness.manifest import HarnessManifest
from archon.models.mock import MockModelAdapter
from archon.subagents import (
    SubagentDefinition,
    SubagentRequest,
    invoke_subagents,
)
from archon.tools import tool


class TestConcurrencyAndLoadStress:
    """Stress tests verifying integrity under 100 concurrent coroutines."""

    @pytest.mark.asyncio
    async def test_100_concurrent_sessions_zero_contamination(self, tmp_path):
        """Verify 100 concurrent sessions maintain complete memory isolation and zero contamination."""
        num_sessions = 100

        async def run_isolated_session(idx: int):
            manifest = HarnessManifest(
                constitution=f"# Constitution Session {idx}",
                rules={f"rule_{idx}.md": f"Rule content {idx}"},
            )
            model = MockModelAdapter(
                canned_responses=[
                    StepResult(text=f"Session {idx} done", is_complete=True)
                ]
            )
            session = AgentSession(
                session_id=f"sess-stress-{idx}",
                manifest=manifest,
                model_adapter=model,
                working_directory=tmp_path,
            )

            # Register unique tool per session
            @tool(name=f"tool_for_{idx}")
            def session_specific_tool() -> int:
                return idx

            session.tool_registry.register(session_specific_tool)

            # Execute run
            res = await session.async_run(f"Task for session {idx}")

            # Verify prompt and isolation
            prompt = session.compile_system_prompt()
            assert f"Session {idx}" in prompt
            assert f"tool_for_{idx}" in session.tool_registry
            assert res.text == f"Session {idx} done"

            # Check that other tools are not present
            assert f"tool_for_{(idx + 1) % num_sessions}" not in session.tool_registry

            session.close()
            assert session.is_closed is True
            return idx

        tasks = [run_isolated_session(i) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks)

        assert len(results) == num_sessions
        assert set(results) == set(range(num_sessions))

    @pytest.mark.asyncio
    async def test_100_concurrent_subagent_invocations(self, tmp_path):
        """Verify 100 subagent requests dispatched concurrently across semaphore throttle without deadlocks."""
        num_subagents = 100
        subagents = {
            f"worker_{i}": SubagentDefinition(
                name=f"worker_{i}",
                system_prompt=f"Worker {i} instructions",
            )
            for i in range(num_subagents)
        }
        manifest = HarnessManifest(constitution="Stress Constitution", subagents=subagents)

        class EchoModel(MockModelAdapter):
            async def async_generate(self, messages, tools=None):
                user_msg = messages[-1]["content"]
                await asyncio.sleep(0.001)  # small yield to stress scheduler
                return StepResult(text=f"Processed: {user_msg}", is_complete=True)

        session = AgentSession(
            session_id="sess-subagent-stress",
            manifest=manifest,
            model_adapter=EchoModel(),
            working_directory=tmp_path,
            concurrency_limit=10,  # Max 10 concurrent
        )

        requests = [
            SubagentRequest(subagent_name=f"worker_{i}", prompt=f"Work item {i}")
            for i in range(num_subagents)
        ]

        results = await invoke_subagents(session, requests)

        assert len(results) == num_subagents
        for i, res in enumerate(results):
            assert res.is_success is True
            assert res.subagent_name == f"worker_{i}"
            assert f"Work item {i}" in res.output

        session.close()
