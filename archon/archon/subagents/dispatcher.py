"""Subagent dispatcher orchestrating parallel asynchronous execution with governance limits."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, List, Sequence

from archon.exceptions import (
    SubagentCycleDetectedError,
    SubagentDepthExceededError,
    SubagentNotFoundError,
)
from archon.subagents.definition import SubagentRequest, SubagentResult

if TYPE_CHECKING:
    from archon.core.context import ExecutionContext


class SubagentDispatcher:
    """Dispatches multiple subagents concurrently with depth, cycle, and semaphore limits."""

    def __init__(self, concurrency_limit: int = 10, max_depth: int = 3) -> None:
        self.concurrency_limit = concurrency_limit
        self.max_depth = max_depth
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    def _validate_request(
        self,
        session: Any,
        request: SubagentRequest,
        context: ExecutionContext,
    ) -> None:
        """Validate request against manifest existence, depth limits, and cycle detection."""
        # 1. Depth check
        if context.depth >= self.max_depth:
            raise SubagentDepthExceededError(
                f"Subagent recursion depth ({context.depth}) exceeded max limit ({self.max_depth}). "
                f"Lineage: {' -> '.join(context.caller_lineage)}"
            )

        # 2. Manifest existence check
        if not hasattr(session, "manifest") or request.subagent_name not in session.manifest.subagents:
            raise SubagentNotFoundError(
                f"Subagent '{request.subagent_name}' is not defined in the harness manifest."
            )

        # 3. Cycle detection check
        if request.subagent_name in context.caller_lineage:
            raise SubagentCycleDetectedError(
                f"Circular subagent invocation cycle detected: "
                f"{' -> '.join(context.caller_lineage)} -> {request.subagent_name}"
            )

    async def _run_single(
        self,
        session: Any,
        request: SubagentRequest,
        context: ExecutionContext,
    ) -> SubagentResult:
        """Execute a single subagent under semaphore and timeout control."""
        from archon.subagents.runner import SubagentRunner

        subagent_def = session.manifest.subagents[request.subagent_name]
        runner = SubagentRunner(session)

        async with self._semaphore:
            return await runner.run(subagent_def, request, context)

    async def dispatch(
        self,
        session: Any,
        requests: Sequence[SubagentRequest],
        context: ExecutionContext,
    ) -> List[SubagentResult]:
        """Dispatch a sequence of subagent requests in parallel."""
        # Pre-validate all requests before launching tasks
        for req in requests:
            self._validate_request(session, req, context)

        tasks = [self._run_single(session, req, context) for req in requests]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[SubagentResult] = []
        for i, res in enumerate(raw_results):
            if isinstance(res, SubagentResult):
                results.append(res)
            elif isinstance(res, Exception):
                results.append(
                    SubagentResult(
                        subagent_name=requests[i].subagent_name,
                        is_success=False,
                        error=str(res),
                    )
                )
        return results


async def invoke_subagents(
    session: Any,
    requests: Sequence[SubagentRequest],
    context: Optional[ExecutionContext] = None,
    concurrency_limit: int = 10,
    max_depth: int = 3,
) -> List[SubagentResult]:
    """Top-level helper to dispatch subagents asynchronously."""
    from archon.core.context import ExecutionContext

    ctx = context or ExecutionContext(
        session_id=getattr(session, "session_id", "default_sess")
    )
    dispatcher = getattr(session, "dispatcher", None)
    if dispatcher is None:
        dispatcher = SubagentDispatcher(
            concurrency_limit=concurrency_limit,
            max_depth=max_depth,
        )
    return await dispatcher.dispatch(session, requests, ctx)
