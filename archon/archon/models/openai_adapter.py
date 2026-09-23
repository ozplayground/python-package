"""OpenAI protocol model adapter with HTTPX, streaming, jitter retry, and tool call parsing."""
from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from archon.core.step import StepResult
from archon.exceptions import (
    ModelAuthenticationError,
    ModelMaxRetriesExceededError,
    ToolCallChunkStreamError,
)
from archon.models.base import BaseModelAdapter


class OpenAIAdapter(BaseModelAdapter):
    """Adapter for OpenAI Chat Completions API and compatible endpoints."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
        max_retries: int = 3,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_retries = max_retries
        self._custom_client = http_client

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        client: httpx.AsyncClient,
    ) -> httpx.Response:
        """Execute request with Full Jitter exponential backoff retry."""
        attempt = 0
        last_error = None

        while attempt <= self.max_retries:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60.0,
                )

                if response.status_code in (401, 403):
                    raise ModelAuthenticationError(
                        f"Authentication failed for OpenAI API: status {response.status_code}. Verify API key credentials."
                    )

                if response.status_code in (429, 500, 502, 503, 504):
                    attempt += 1
                    if attempt > self.max_retries:
                        raise ModelMaxRetriesExceededError(
                            f"OpenAI API request exceeded max retries ({self.max_retries}). Last status: {response.status_code}."
                        )
                    # Full Jitter: random(0, min(30.0, 1.0 * (2 ** attempt)))
                    sleep_time = random.uniform(0, min(30.0, 1.0 * (2 ** attempt)))
                    await asyncio.sleep(sleep_time)
                    continue

                response.raise_for_status()
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                attempt += 1
                last_error = e
                if attempt > self.max_retries:
                    raise ModelMaxRetriesExceededError(
                        f"OpenAI connection failed after {self.max_retries} retries: {e}"
                    ) from e
                sleep_time = random.uniform(0, min(30.0, 1.0 * (2 ** attempt)))
                await asyncio.sleep(sleep_time)

        raise ModelMaxRetriesExceededError(f"OpenAI request failed: {last_error}")

    async def async_generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> StepResult:
        """Call OpenAI Chat Completions endpoint."""
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools

        client = self._custom_client or httpx.AsyncClient()
        should_close = self._custom_client is None

        try:
            resp = await self._request_with_retry("/chat/completions", payload, client)
            data = resp.json()

            choices = data.get("choices", [])
            if not choices:
                return StepResult(text="", is_complete=True)

            choice = choices[0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""
            finish_reason = choice.get("finish_reason", "stop")

            # Parse tool calls
            tool_calls = []
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    parsed_args = {"raw": raw_args}
                tool_calls.append({"name": fn_name, "arguments": parsed_args})

            usage = data.get("usage", {})
            return StepResult(
                text=content,
                tool_calls=tool_calls,
                is_complete=(finish_reason == "stop" and not tool_calls),
                metadata={
                    "finish_reason": finish_reason,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "model": data.get("model", self.model_name),
                },
            )
        finally:
            if should_close:
                await client.aclose()

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
        """Stream response tokens using server-sent events (SSE)."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }

        client = self._custom_client or httpx.AsyncClient()
        should_close = self._custom_client is None

        try:
            resp = await self._request_with_retry("/chat/completions", payload, client)
            lines = resp.text.splitlines()

            for line in lines:
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    raw_chunk = line[6:]
                    try:
                        chunk_data = json.loads(raw_chunk)
                        choices = chunk_data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
        finally:
            if should_close:
                await client.aclose()
