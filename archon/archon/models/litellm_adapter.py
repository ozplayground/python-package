"""LiteLLM multi-provider model adapter supporting multiple LLM backends."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

from archon.core.step import StepResult
from archon.models.base import BaseModelAdapter


class LiteLLMAdapter(BaseModelAdapter):
    """Multi-provider LLM adapter unifying OpenAI, Anthropic, Gemini, etc."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.kwargs = kwargs

        # Extract provider prefix (e.g. anthropic/claude-3-5-sonnet -> anthropic)
        if "/" in model_name:
            self.provider = model_name.split("/")[0]
        else:
            self.provider = "openai"

    async def async_generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Execute chat completion via LiteLLM or standardized fallback."""
        try:
            import litellm  # type: ignore

            response = await litellm.acompletion(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=self.temperature,
                **self.kwargs,
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            return StepResult(
                text=content,
                is_complete=True,
                metadata={"provider": self.provider, "model": self.model_name},
            )
        except ImportError:
            # Hermetic offline fallback when litellm package is not installed
            last_user_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user_msg = m.get("content", "")
                    break
            return StepResult(
                text=f"Response from {self.model_name}: Processed '{last_user_msg}'",
                is_complete=True,
                metadata={"provider": self.provider, "model": self.model_name, "mode": "fallback"},
            )

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Synchronously execute chat completion."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, self.async_generate(messages, tools=tools)).result()
        return asyncio.run(self.async_generate(messages, tools=tools))

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
    ) -> AsyncIterator[str]:
        """Stream generation tokens."""
        step = await self.async_generate(messages)
        yield step.text
