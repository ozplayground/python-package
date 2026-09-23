"""Factory for creating and initializing AgentSession instances."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional, Sequence, Union

from archon.core.session import AgentSession
from archon.harness.fs_provider import FileSystemHarnessProvider
from archon.harness.manifest import HarnessManifest
from archon.harness.memory_provider import InMemoryHarnessProvider
from archon.harness.provider import HarnessProvider
from archon.models.base import BaseModelAdapter
from archon.models.mock import MockModelAdapter
from archon.tools.base import BaseTool


def create_session(
    harness: Union[HarnessProvider, HarnessManifest, Path, str, bytes],
    *,
    model: Union[str, BaseModelAdapter] = "gpt-4o",
    session_id: Optional[str] = None,
    concurrency_limit: int = 10,
    session_timeout: float = 600.0,
    subagent_timeout: float = 120.0,
    working_directory: Optional[Union[Path, str]] = None,
    custom_tools: Optional[Sequence[BaseTool]] = None,
) -> AgentSession:
    """Create an isolated AgentSession dynamically compiled from a harness source.

    Args:
        harness: HarnessProvider instance, compiled HarnessManifest, local directory path, or zip archive bytes.
        model: LLM model adapter or string identifier.
        session_id: Optional unique session ID; if omitted, a new UUID is generated.
        concurrency_limit: Maximum concurrent subagents (default: 10).
        session_timeout: Maximum session lifetime in seconds (default: 600.0).
        subagent_timeout: Maximum subagent run timeout in seconds (default: 120.0).
        working_directory: Working directory path for sandboxed bash execution.
        custom_tools: Optional sequence of custom tools to register in the session registry.

    Returns:
        Configured and isolated AgentSession instance.
    """
    if isinstance(harness, HarnessManifest):
        manifest = harness
    elif isinstance(harness, HarnessProvider):
        manifest = harness.load()
    elif isinstance(harness, bytes):
        manifest = InMemoryHarnessProvider(harness).load()
    elif isinstance(harness, (str, Path)):
        manifest = FileSystemHarnessProvider(harness).load()
    else:
        raise TypeError(f"Unsupported harness source type: {type(harness)}")

    # Model resolution
    if isinstance(model, BaseModelAdapter):
        model_adapter = model
    elif isinstance(model, str):
        try:
            from archon.models.openai_adapter import OpenAIAdapter
            model_adapter = OpenAIAdapter(model_name=model)
        except Exception:
            try:
                from archon.models.litellm_adapter import LiteLLMAdapter
                model_adapter = LiteLLMAdapter(model_name=model)
            except Exception:
                model_adapter = MockModelAdapter()
    else:
        model_adapter = MockModelAdapter()

    sid = session_id or f"sess_{uuid.uuid4()}"
    session = AgentSession(
        session_id=sid,
        manifest=manifest,
        model_adapter=model_adapter,
        working_directory=working_directory,
        concurrency_limit=concurrency_limit,
        session_timeout=session_timeout,
        subagent_timeout=subagent_timeout,
    )

    if custom_tools:
        for t in custom_tools:
            session.tool_registry.register(t)

    return session
