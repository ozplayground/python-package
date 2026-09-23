"""End-to-End integration test covering full harness compilation, tools, and multi-subagent dispatch."""
from pathlib import Path
import pytest

from archon import create_session
from archon.core.step import StepResult
from archon.models import MockModelAdapter
from archon.subagents import SubagentRequest
from archon.tools import tool


class TestArchonEndToEnd:
    """Full workflow E2E test."""

    @pytest.mark.asyncio
    async def test_full_agent_workflow(self, tmp_path):
        # 1. Prepare realistic harness directory
        (tmp_path / "AGENTS.md").write_text("# Production Agent Constitution\nLead with high quality code.")

        rules_dir = tmp_path / ".agents" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "01_standards.md").write_text("All code must have tests.")

        # Skills
        skills_dir = tmp_path / ".agents" / "skills"
        tdd_dir = skills_dir / "tdd"
        tdd_dir.mkdir(parents=True)
        (tdd_dir / "SKILL.md").write_text(
            "---\nname: tdd\ndescription: TDD methodology\n---\nWrite failing tests first before logic."
        )

        sec_dir = skills_dir / "sec_audit"
        sec_dir.mkdir(parents=True)
        (sec_dir / "SKILL.md").write_text(
            "---\nname: sec_audit\ndescription: Security audit\n---\nCheck for OWASP Top 10 vulnerabilities."
        )

        # Subagents
        subagents_dir = tmp_path / ".agents" / "subagents"
        subagents_dir.mkdir(parents=True)
        (subagents_dir / "backend_dev.md").write_text(
            "---\nname: backend_dev\ndescription: Backend Developer\nallowed_tools: [bash]\nrequired_skills: [tdd]\n---\nYou are a Senior Backend Engineer."
        )
        (subagents_dir / "sec_officer.md").write_text(
            "---\nname: sec_officer\ndescription: Security Officer\nallowed_tools: []\nrequired_skills: [sec_audit]\n---\nYou are a Chief Security Architect."
        )

        # 2. Setup mock model responses
        # Main turn 1: invokes custom tool
        step1_tool_call = StepResult(
            text="Calculating deployment hash...",
            tool_calls=[{"name": "hash_calc", "arguments": {"salt": 42}}],
            is_complete=False,
        )
        # Main turn 2: completes direct tool phase
        step2_completion = StepResult(
            text="Hash calculated. Proceeding with subagent dispatch.",
            is_complete=True,
        )

        # Subagent responses
        backend_response = StepResult(text="API endpoints implemented with 100% test coverage.", is_complete=True)
        sec_response = StepResult(text="Security audit passed: 0 vulnerabilities found.", is_complete=True)

        model = MockModelAdapter(
            canned_responses=[
                step1_tool_call,
                step2_completion,
                backend_response,
                sec_response,
            ]
        )

        @tool(name="hash_calc")
        def hash_calc(salt: int) -> str:
            return f"sha256-salt-{salt}"

        # 3. Create session via top-level factory
        session = create_session(
            harness=tmp_path,
            model=model,
            working_directory=tmp_path,
            custom_tools=[hash_calc],
        )

        assert session.session_id is not None
        assert "Production Agent Constitution" in session.compile_system_prompt()
        assert "hash_calc" in session.tool_registry

        # 4. Run main agent turn with tool execution
        main_res = await session.async_run("Initialize release process")
        assert "Hash calculated" in main_res.text
        assert main_res.is_complete is True

        # 5. Dispatch multiple subagents concurrently
        requests = [
            SubagentRequest(subagent_name="backend_dev", prompt="Implement payment endpoint"),
            SubagentRequest(subagent_name="sec_officer", prompt="Audit payment code"),
        ]
        sub_results = await session.invoke_subagents(requests)

        assert len(sub_results) == 2
        assert sub_results[0].subagent_name == "backend_dev"
        assert sub_results[0].is_success is True
        assert "100% test coverage" in sub_results[0].output

        assert sub_results[1].subagent_name == "sec_officer"
        assert sub_results[1].is_success is True
        assert "0 vulnerabilities found" in sub_results[1].output

        # 6. Clean termination
        session.close()
        assert session.is_closed is True
