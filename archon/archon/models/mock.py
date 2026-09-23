"""Deterministic mock model adapter for hermetic TDD testing."""
from typing import Any, Dict, List, Optional

from archon.core.step import StepResult
from archon.models.base import BaseModelAdapter


class MockModelAdapter(BaseModelAdapter):
    """Mock adapter returning pre-configured canned responses in FIFO order."""

    def __init__(self, canned_responses: Optional[List[StepResult]] = None) -> None:
        self.canned_responses: List[StepResult] = list(canned_responses or [])
        self.calls: List[Dict[str, Any]] = []

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Record the call and return the next canned response."""
        self.calls.append({"messages": messages, "tools": tools})
        if self.canned_responses:
            return self.canned_responses.pop(0)
        return StepResult(text="Mock default response", is_complete=True)

    async def async_generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Asynchronously return the next canned response."""
        return self.generate(messages, tools)
