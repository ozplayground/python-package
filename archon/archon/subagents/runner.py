"""Subagent runner executing isolated subagent turn loops with skill injection and timeout."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List

from archon.exceptions import SessionClosedError
from archon.subagents.definition import (
    SubagentDefinition,
    SubagentRequest,
    SubagentResult,
)

if TYPE_CHECKING:
    from archon.core.context import ExecutionContext


class SubagentRunner:
    """Executes a single subagent task under isolation, skill injection, and timeout control."""

    def __init__(self, session: Any) -> None:
        self.session = session

    async def run(
        self,
        subagent_def: SubagentDefinition,
        request: SubagentRequest,
        context: ExecutionContext,
    ) -> SubagentResult:
        """Run the subagent lifecycle."""
        start_time = time.perf_counter()
        timeout = request.timeout_seconds or subagent_def.timeout_seconds or 120.0

        if hasattr(self.session, "message_bus") and self.session.message_bus:
            await self.session.message_bus.publish(
                "SUBAGENT_STARTED",
                {"subagent_name": request.subagent_name, "prompt": request.prompt},
            )

        try:
            output = await asyncio.wait_for(
                self._execute_run(subagent_def, request, context),
                timeout=timeout,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if hasattr(self.session, "message_bus") and self.session.message_bus:
                await self.session.message_bus.publish(
                    "SUBAGENT_COMPLETED",
                    {"subagent_name": request.subagent_name, "output": output},
                )

            return SubagentResult(
                subagent_name=request.subagent_name,
                is_success=True,
                output=str(output),
                duration_ms=round(duration_ms, 2),
            )
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Subagent '{request.subagent_name}' execution timed out after {timeout}s."
            if hasattr(self.session, "message_bus") and self.session.message_bus:
                await self.session.message_bus.publish(
                    "SUBAGENT_FAILED",
                    {"subagent_name": request.subagent_name, "error": error_msg},
                )
            return SubagentResult(
                subagent_name=request.subagent_name,
                is_success=False,
                is_timeout=True,
                output="",
                error=error_msg,
                duration_ms=round(duration_ms, 2),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = str(e)
            if hasattr(self.session, "message_bus") and self.session.message_bus:
                await self.session.message_bus.publish(
                    "SUBAGENT_FAILED",
                    {"subagent_name": request.subagent_name, "error": error_msg},
                )
            return SubagentResult(
                subagent_name=request.subagent_name,
                is_success=False,
                is_timeout=False,
                output="",
                error=error_msg,
                duration_ms=round(duration_ms, 2),
            )

    async def _execute_run(
        self,
        subagent_def: SubagentDefinition,
        request: SubagentRequest,
        context: ExecutionContext,
    ) -> str:
        if getattr(self.session, "is_closed", False):
            raise SessionClosedError("Session is closed.")

        if hasattr(self.session, "execute_subagent_run"):
            return await self.session.execute_subagent_run(subagent_def, request, context)

        # Fallback direct execution
        sections = [subagent_def.system_prompt]
        if subagent_def.required_skills and hasattr(self.session, "skill_registry"):
            injected_skills = self.session.skill_registry.get_prompt_injection(
                subagent_def.required_skills
            )
            if injected_skills:
                sections.append(f"## Injected Skills\n{injected_skills}")

        system_prompt = "\n\n".join(sections)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.prompt},
        ]
        step = await self.session.model_adapter.async_generate(messages)
        return step.text
