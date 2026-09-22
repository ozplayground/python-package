"""quiver.timing: High-precision monotonic stopwatch, code execution timer, and rate limiter.

Provides Stopwatch with lap tracking, measure_time context/decorator, and
thread-safe Token Bucket RateLimiter.
"""

import asyncio
from dataclasses import dataclass
import functools
import inspect
import threading
import time
from typing import (
    Any,
    Callable,
    Literal,
    Optional,
    ParamSpec,
    TypeVar,
)

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class LapRecord:
    """Immutable record of a stopwatch lap interval and cumulative time."""

    index: int
    name: Optional[str]
    lap_time_ns: int
    total_time_ns: int
    lap_seconds: float
    total_seconds: float


class Stopwatch:
    """Thread-safe monotonic stopwatch with lap time recording."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_ns: int = 0
        self._accumulated_ns: int = 0
        self._last_lap_ns: int = 0
        self._is_running: bool = False
        self._laps: list[LapRecord] = []

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @property
    def elapsed_ns(self) -> int:
        with self._lock:
            if self._is_running:
                return self._accumulated_ns + (time.perf_counter_ns() - self._start_ns)
            return self._accumulated_ns

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ns / 1_000_000_000.0

    @property
    def laps(self) -> list[LapRecord]:
        with self._lock:
            return list(self._laps)

    def start(self) -> "Stopwatch":
        """Start or resume the stopwatch."""
        with self._lock:
            if not self._is_running:
                self._start_ns = time.perf_counter_ns()
                self._is_running = True
        return self

    def stop(self) -> float:
        """Stop the stopwatch and return elapsed seconds."""
        with self._lock:
            if self._is_running:
                now = time.perf_counter_ns()
                self._accumulated_ns += now - self._start_ns
                self._is_running = False
            return self._accumulated_ns / 1_000_000_000.0

    def reset(self) -> "Stopwatch":
        """Reset the stopwatch to initial zero state."""
        with self._lock:
            self._start_ns = 0
            self._accumulated_ns = 0
            self._last_lap_ns = 0
            self._is_running = False
            self._laps.clear()
        return self

    def lap(self, name: Optional[str] = None) -> LapRecord:
        """Record a lap timestamp and interval."""
        with self._lock:
            now_ns = (
                self._accumulated_ns + (time.perf_counter_ns() - self._start_ns)
                if self._is_running
                else self._accumulated_ns
            )
            lap_ns = now_ns - self._last_lap_ns
            self._last_lap_ns = now_ns
            rec = LapRecord(
                index=len(self._laps),
                name=name,
                lap_time_ns=lap_ns,
                total_time_ns=now_ns,
                lap_seconds=lap_ns / 1_000_000_000.0,
                total_seconds=now_ns / 1_000_000_000.0,
            )
            self._laps.append(rec)
            return rec

    def __enter__(self) -> "Stopwatch":
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


_UNIT_DIVISORS = {
    "s": 1_000_000_000.0,
    "ms": 1_000_000.0,
    "us": 1_000.0,
    "ns": 1.0,
}


class MeasureTimeContext:
    """Context manager and decorator for measuring execution duration."""

    def __init__(
        self,
        callback: Optional[Callable[[float], None]],
        unit: Literal["s", "ms", "us", "ns"],
    ) -> None:
        if unit not in _UNIT_DIVISORS:
            raise ValueError(
                f"Unsupported unit: {unit!r}. Must be one of ('s', 'ms', 'us', 'ns')"
            )
        self._callback = callback
        self._unit = unit
        self._divisor = _UNIT_DIVISORS[unit]
        self._start_ns: int = 0
        self._elapsed_ns: int = 0

    @property
    def elapsed_ns(self) -> int:
        return self._elapsed_ns

    @property
    def elapsed(self) -> float:
        return self._elapsed_ns / self._divisor

    @property
    def unit(self) -> str:
        return self._unit

    def __enter__(self) -> "MeasureTimeContext":
        self._start_ns = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._elapsed_ns = time.perf_counter_ns() - self._start_ns
        if self._callback is not None:
            self._callback(self.elapsed)

    def __call__(self, fn: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.perf_counter_ns()
                try:
                    return await fn(*args, **kwargs)  # type: ignore
                finally:
                    dur_ns = time.perf_counter_ns() - start
                    val = dur_ns / self._divisor
                    if self._callback is not None:
                        self._callback(val)

            return _async_wrapper  # type: ignore
        else:

            @functools.wraps(fn)
            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.perf_counter_ns()
                try:
                    return fn(*args, **kwargs)
                finally:
                    dur_ns = time.perf_counter_ns() - start
                    val = dur_ns / self._divisor
                    if self._callback is not None:
                        self._callback(val)

            return _sync_wrapper


def measure_time(
    callback: Optional[Callable[[float], None]] = None,
    unit: Literal["s", "ms", "us", "ns"] = "ms",
) -> MeasureTimeContext:
    """Measure block or function execution duration in the requested unit."""
    return MeasureTimeContext(callback, unit)


class RateLimiter:
    """Thread-safe Token Bucket rate limiter."""

    def __init__(
        self,
        rate: float,
        per_seconds: float = 1.0,
        burst: Optional[float] = None,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be > 0")
        if per_seconds <= 0:
            raise ValueError("per_seconds must be > 0")
        if burst is not None and burst <= 0:
            raise ValueError("burst must be > 0")

        self._rate = float(rate)
        self._per_seconds = float(per_seconds)
        self._burst = float(rate if burst is None else burst)
        self._fill_rate = self._rate / self._per_seconds
        self._tokens = self._burst
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def per_seconds(self) -> float:
        return self._per_seconds

    @property
    def burst(self) -> float:
        return self._burst

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill(time.monotonic())
            return self._tokens

    def _refill(self, now: float) -> None:
        delta = now - self._last_refill
        if delta > 0:
            self._tokens = min(self._burst, self._tokens + delta * self._fill_rate)
            self._last_refill = now

    def acquire(
        self,
        tokens: float = 1.0,
        blocking: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """Acquire `tokens` from the bucket. Blocks or returns False if not available."""
        if tokens <= 0:
            raise ValueError("tokens must be > 0")
        if tokens > self._burst:
            raise ValueError(
                f"Requested tokens ({tokens}) exceeds burst capacity ({self._burst})"
            )

        start_time = time.monotonic()
        while True:
            with self._lock:
                now = time.monotonic()
                self._refill(now)
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                if not blocking:
                    return False

                needed = tokens - self._tokens
                wait_time = needed / self._fill_rate

                if timeout is not None:
                    elapsed = now - start_time
                    remaining_timeout = timeout - elapsed
                    if remaining_timeout <= 0 or wait_time > remaining_timeout:
                        return False
                    sleep_duration = min(wait_time, remaining_timeout)
                else:
                    sleep_duration = wait_time

            time.sleep(min(sleep_duration, 0.05))

    def __enter__(self) -> bool:
        return self.acquire(tokens=1.0, blocking=True)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def __aenter__(self) -> bool:
        return await asyncio.to_thread(self.acquire, tokens=1.0, blocking=True)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def __call__(self, fn: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def _async_wrap(*args: P.args, **kwargs: P.kwargs) -> R:
                self.acquire(tokens=1.0, blocking=True)
                return await fn(*args, **kwargs)  # type: ignore

            return _async_wrap  # type: ignore
        else:

            @functools.wraps(fn)
            def _sync_wrap(*args: P.args, **kwargs: P.kwargs) -> R:
                self.acquire(tokens=1.0, blocking=True)
                return fn(*args, **kwargs)

            return _sync_wrap
