"""Exponential backoff and Full Jitter retry engine for HTTP requests."""
import asyncio
import email.utils
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Mapping, Optional, Tuple
import httpx

from courier.config import RetryConfig


class RetryEngine:
    """Resilient retry engine implementing exponential backoff with full jitter and Retry-After support."""

    def __init__(self, config: RetryConfig) -> None:
        self.config = config

    def _parse_retry_after(self, headers: Mapping[str, str]) -> Optional[float]:
        """Parse Retry-After header either as integer seconds or HTTP-Date."""
        retry_after_val: Optional[str] = None
        for k, v in headers.items():
            if k.lower() == "retry-after":
                retry_after_val = v
                break
        if not retry_after_val:
            return None

        # Try parsing as integer seconds
        try:
            return float(retry_after_val.strip())
        except ValueError:
            pass

        # Try parsing as HTTP-Date
        try:
            parsed_date = email.utils.parsedate_to_datetime(retry_after_val.strip())
            now = datetime.now(timezone.utc)
            delta = (parsed_date - now).total_seconds()
            return max(0.0, delta)
        except Exception:
            return None

    def execute_sync(
        self,
        call_fn: Callable[[], httpx.Response],
        is_idempotent: bool = True,
    ) -> Tuple[Optional[httpx.Response], Optional[Exception], float]:
        """Execute synchronous HTTP call with retry logic."""
        start_time = time.perf_counter()
        attempt = 0
        can_retry_method = is_idempotent or self.config.retry_on_post

        while True:
            response: Optional[httpx.Response] = None
            exception: Optional[Exception] = None

            try:
                response = call_fn()
            except Exception as e:
                exception = e

            # Case 1: Exception occurred
            if exception is not None:
                if (
                    can_retry_method
                    and attempt < self.config.max_retries
                    and self.config.is_retryable_exception(exception)
                ):
                    wait_time = self.config.calculate_wait_time(attempt)
                    time.sleep(wait_time)
                    attempt += 1
                    continue
                else:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    return None, exception, duration_ms

            # Case 2: Response received
            if response is not None:
                if (
                    can_retry_method
                    and attempt < self.config.max_retries
                    and self.config.is_retryable_status(response.status_code)
                ):
                    retry_after = self._parse_retry_after(response.headers)
                    if retry_after is not None and retry_after > self.config.max_backoff_seconds:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        return response, None, duration_ms

                    wait_time = self.config.calculate_wait_time(attempt, retry_after)
                    time.sleep(wait_time)
                    attempt += 1
                    continue
                else:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    return response, None, duration_ms

    async def execute_async(
        self,
        call_fn: Callable[[], Awaitable[httpx.Response]],
        is_idempotent: bool = True,
    ) -> Tuple[Optional[httpx.Response], Optional[Exception], float]:
        """Execute asynchronous HTTP call with retry logic."""
        start_time = time.perf_counter()
        attempt = 0
        can_retry_method = is_idempotent or self.config.retry_on_post

        while True:
            response: Optional[httpx.Response] = None
            exception: Optional[Exception] = None

            try:
                response = await call_fn()
            except Exception as e:
                exception = e

            # Case 1: Exception occurred
            if exception is not None:
                if (
                    can_retry_method
                    and attempt < self.config.max_retries
                    and self.config.is_retryable_exception(exception)
                ):
                    wait_time = self.config.calculate_wait_time(attempt)
                    await asyncio.sleep(wait_time)
                    attempt += 1
                    continue
                else:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    return None, exception, duration_ms

            # Case 2: Response received
            if response is not None:
                if (
                    can_retry_method
                    and attempt < self.config.max_retries
                    and self.config.is_retryable_status(response.status_code)
                ):
                    retry_after = self._parse_retry_after(response.headers)
                    if retry_after is not None and retry_after > self.config.max_backoff_seconds:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        return response, None, duration_ms

                    wait_time = self.config.calculate_wait_time(attempt, retry_after)
                    await asyncio.sleep(wait_time)
                    attempt += 1
                    continue
                else:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    return response, None, duration_ms
