"""Abstract base model adapter interface."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from archon.core.step import StepResult


class BaseModelAdapter(ABC):
    """Abstract adapter unifying LLM vendor APIs (OpenAI, Anthropic, Mock)."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Synchronously generate a step result from conversation messages and tool schemas."""

    async def async_generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Asynchronously generate a step result."""
        # Default fallback to synchronous execution
        return self.generate(messages, tools)

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
    ) -> AsyncIterator[str]:
        """Stream text tokens asynchronously."""
        res = await self.async_generate(messages)
        yield res.text
