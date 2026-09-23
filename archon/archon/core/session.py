"""Agent session managing harness manifest, tool/skill registries, and turn execution loops."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Mapping, Optional, Sequence, Union

from archon.core.context import ExecutionContext
from archon.core.step import StepResult
from archon.exceptions import SessionClosedError, SessionTimeoutError
from archon.models.base import BaseModelAdapter
from archon.skills.registry import SkillRegistry
from archon.subagents.bus import MessageBus
from archon.subagents.definition import (
    SubagentDefinition,
    SubagentRequest,
    SubagentResult,
)
from archon.subagents.dispatcher import SubagentDispatcher
from archon.tools.bash import BashTool
from archon.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from archon.harness.manifest import HarnessManifest


class AgentSession:
    """Active execution session binding harness governance to an agent lifecycle."""

    def __init__(
        self,
        session_id: str,
        manifest: HarnessManifest,
        model_adapter: BaseModelAdapter,
        working_directory: Optional[Union[str, Path]] = None,
        tool_registry: Optional[ToolRegistry] = None,
        skill_registry: Optional[SkillRegistry] = None,
        concurrency_limit: int = 10,
        session_timeout: float = 600.0,
        subagent_timeout: float = 120.0,
    ) -> None:
        self.session_id = session_id
        self.manifest = manifest
        self.model_adapter = model_adapter
        self.working_directory = Path(working_directory or Path.cwd()).resolve()

        # Tool Registry initialization
        self.tool_registry = (
            tool_registry.clone() if tool_registry else ToolRegistry()
        )
        if "bash" not in self.tool_registry:
            self.tool_registry.register(BashTool(working_directory=self.working_directory))

        # Skill Registry initialization
        self.skill_registry = (
            skill_registry if skill_registry else SkillRegistry(manifest.skills)
        )

        self.message_bus = MessageBus()
        self.dispatcher = SubagentDispatcher(concurrency_limit=concurrency_limit)
        self.session_timeout = session_timeout
        self.subagent_timeout = subagent_timeout
        self._is_closed = False

    @property
    def is_closed(self) -> bool:
        """True if session resources have been terminated."""
        return self._is_closed

    def compile_system_prompt(self, agent_name: str = "main") -> str:
        """Compile immutable harness constitution, rules, and skills into a system prompt."""
        sections = [self.manifest.constitution]

        if self.manifest.rules:
            sections.append("## Project Rules")
            for filename, rule_content in sorted(self.manifest.rules.items()):
                sections.append(f"### {filename}\n{rule_content}")

        return "\n\n".join(sections)

    async def execute_subagent_run(
        self,
        subagent_def: SubagentDefinition,
        request: SubagentRequest,
        child_context: ExecutionContext,
    ) -> str:
        """Execute a subagent turn loop with isolated prompt and required skills."""
        if self._is_closed:
            raise SessionClosedError(f"Session '{self.session_id}' is closed.")

        sections = [subagent_def.system_prompt]
        if subagent_def.required_skills:
            injected_skills = self.skill_registry.get_prompt_injection(
                subagent_def.required_skills
            )
            if injected_skills:
                sections.append(f"## Injected Skills\n{injected_skills}")

        system_prompt = "\n\n".join(sections)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.prompt},
        ]

        step = await self.model_adapter.async_generate(messages)
        return step.text

    async def _execute_turn_loop(
        self,
        prompt: str,
        context: Optional[Mapping[str, Any]] = None,
    ) -> StepResult:
        system_prompt = self.compile_system_prompt()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        last_step = StepResult(text="", is_complete=False)
        max_turns = 10

        for _ in range(max_turns):
            step = await self.model_adapter.async_generate(
                messages, tools=self.tool_registry.get_schemas()
            )
            last_step = step

            if not step.tool_calls:
                break

            # Execute tool calls
            for tool_call in step.tool_calls:
                fn_name = tool_call.get("name", "")
                fn_args = tool_call.get("arguments", {})
                tool = self.tool_registry.get(fn_name)

                if tool:
                    tool_res = tool.execute(**fn_args)
                    res_content = (
                        tool_res.stdout
                        if tool_res.is_success
                        else f"Error: {tool_res.error}"
                    )
                else:
                    res_content = f"Error: Tool '{fn_name}' not found."

                messages.append({"role": "assistant", "content": step.text, "tool_calls": [tool_call]})
                messages.append({"role": "tool", "name": fn_name, "content": res_content})

            if step.is_complete:
                break

        return last_step

    async def async_run(
        self,
        prompt: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> StepResult:
        """Execute main agent turn loop asynchronously with session timeout protection."""
        if self._is_closed:
            raise SessionClosedError(f"Session '{self.session_id}' is closed.")

        try:
            return await asyncio.wait_for(
                self._execute_turn_loop(prompt, context=context),
                timeout=self.session_timeout,
            )
        except asyncio.TimeoutError:
            raise SessionTimeoutError(
                f"Session '{self.session_id}' timed out after {self.session_timeout}s."
            )

    def run(
        self,
        prompt: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> StepResult:
        """Synchronously execute main agent turn loop."""
        if self._is_closed:
            raise SessionClosedError(f"Session '{self.session_id}' is closed.")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already inside a running event loop (e.g. jupyter or test harness)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, self.async_run(prompt, context=context)).result()
        else:
            return asyncio.run(self.async_run(prompt, context=context))

    async def stream(
        self,
        prompt: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream text tokens asynchronously."""
        if self._is_closed:
            raise SessionClosedError(f"Session '{self.session_id}' is closed.")

        messages = [
            {"role": "system", "content": self.compile_system_prompt()},
            {"role": "user", "content": prompt},
        ]
        async for chunk in self.model_adapter.stream_generate(messages):
            yield chunk

    async def invoke_subagents(
        self,
        requests: Sequence[SubagentRequest],
    ) -> List[SubagentResult]:
        """Dispatch a sequence of subagent requests in parallel."""
        if self._is_closed:
            raise SessionClosedError(f"Session '{self.session_id}' is closed.")

        root_ctx = ExecutionContext(session_id=self.session_id)
        return await self.dispatcher.dispatch(self, requests, root_ctx)

    def close(self) -> None:
        """Clean up session resources and mark as closed."""
        self._is_closed = True
        self.message_bus.clear()
