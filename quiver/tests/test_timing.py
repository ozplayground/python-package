"""Tests for quiver.timing module.

Covers Stopwatch, LapRecord, measure_time, and RateLimiter.
"""

import asyncio
import time
import pytest

from quiver.timing import (
    LapRecord,
    RateLimiter,
    Stopwatch,
    measure_time,
)


# ==========================================
# 1. Stopwatch tests
# ==========================================
class TestStopwatch:
    def test_stopwatch_start_stop(self):
        sw = Stopwatch()
        assert not sw.is_running
        assert sw.elapsed_ns == 0
        assert sw.elapsed_seconds == 0.0

        sw.start()
        assert sw.is_running
        time.sleep(0.02)
        assert sw.elapsed_ns > 0
        assert sw.elapsed_seconds > 0.01

        stopped_sec = sw.stop()
        assert not sw.is_running
        assert stopped_sec == sw.elapsed_seconds

        # Elapsed time does not increase after stopping
        frozen_time = sw.elapsed_ns
        time.sleep(0.01)
        assert sw.elapsed_ns == frozen_time

    def test_stopwatch_resume(self):
        sw = Stopwatch()
        sw.start()
        time.sleep(0.01)
        sw.stop()
        part1 = sw.elapsed_ns

        sw.start()  # resume
        time.sleep(0.01)
        sw.stop()
        part2 = sw.elapsed_ns
        assert part2 > part1

    def test_stopwatch_reset(self):
        sw = Stopwatch()
        sw.start()
        time.sleep(0.01)
        sw.stop()
        assert sw.elapsed_ns > 0

        sw.reset()
        assert sw.elapsed_ns == 0
        assert not sw.is_running
        assert sw.laps == []

    def test_stopwatch_laps(self):
        sw = Stopwatch()
        sw.start()
        time.sleep(0.01)
        lap1 = sw.lap("checkpoint_1")
        time.sleep(0.02)
        lap2 = sw.lap("checkpoint_2")
        sw.stop()

        assert len(sw.laps) == 2
        assert lap1.index == 0
        assert lap1.name == "checkpoint_1"
        assert lap1.lap_time_ns > 0
        assert lap1.total_time_ns > 0

        assert lap2.index == 1
        assert lap2.name == "checkpoint_2"
        assert lap2.lap_time_ns > 0
        assert lap2.total_time_ns > lap1.total_time_ns

    def test_stopwatch_context_manager(self):
        with Stopwatch() as sw:
            assert sw.is_running
            time.sleep(0.01)
        assert not sw.is_running
        assert sw.elapsed_seconds >= 0.009


# ==========================================
# 2. measure_time tests
# ==========================================
class TestMeasureTime:
    def test_measure_time_context_ms(self):
        with measure_time(unit="ms") as timer:
            time.sleep(0.02)
        assert timer.elapsed >= 15.0  # at least ~15ms
        assert timer.unit == "ms"
        assert timer.elapsed_ns > 0

    def test_measure_time_units(self):
        with measure_time(unit="s") as t_s:
            time.sleep(0.01)
        assert t_s.elapsed >= 0.009
        assert t_s.unit == "s"

        with measure_time(unit="us") as t_us:
            time.sleep(0.005)
        assert t_us.elapsed >= 4000.0
        assert t_us.unit == "us"

        with measure_time(unit="ns") as t_ns:
            time.sleep(0.002)
        assert t_ns.elapsed >= 1_500_000.0
        assert t_ns.unit == "ns"

    def test_measure_time_callback(self):
        measured = []
        with measure_time(callback=lambda el: measured.append(el), unit="ms"):
            time.sleep(0.01)
        assert len(measured) == 1
        assert measured[0] >= 8.0

    def test_measure_time_decorator_sync(self):
        measured = []

        @measure_time(callback=lambda el: measured.append(el), unit="ms")
        def work(x):
            time.sleep(0.01)
            return x * 2

        res = work(5)
        assert res == 10
        assert len(measured) == 1
        assert measured[0] >= 8.0

    @pytest.mark.asyncio
    async def test_measure_time_decorator_async(self):
        measured = []

        @measure_time(callback=lambda el: measured.append(el), unit="ms")
        async def async_work():
            await asyncio.sleep(0.01)
            return "done"

        res = await async_work()
        assert res == "done"
        assert len(measured) == 1

    def test_measure_time_invalid_unit(self):
        with pytest.raises(ValueError, match="Unsupported unit"):
            measure_time(unit="hours")  # type: ignore


# ==========================================
# 3. RateLimiter tests
# ==========================================
class TestRateLimiter:
    def test_rate_limiter_initial_state(self):
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        assert limiter.rate == 10.0
        assert limiter.per_seconds == 1.0
        assert limiter.burst == 10.0
        assert limiter.available_tokens == 10.0

    def test_rate_limiter_acquire_non_blocking(self):
        limiter = RateLimiter(rate=2, per_seconds=1.0, burst=2)
        # Should succeed 2 times immediately
        assert limiter.acquire(1.0, blocking=False) is True
        assert limiter.acquire(1.0, blocking=False) is True
        # 3rd time should fail immediately without blocking
        assert limiter.acquire(1.0, blocking=False) is False

    def test_rate_limiter_refill(self):
        limiter = RateLimiter(rate=10, per_seconds=0.1, burst=5)
        # Consume all 5
        assert limiter.acquire(5.0, blocking=False) is True
        assert limiter.acquire(1.0, blocking=False) is False

        # Sleep 0.05s -> refills 10 * (0.05 / 0.1) = 5 tokens
        time.sleep(0.06)
        assert limiter.acquire(2.0, blocking=False) is True

    def test_rate_limiter_blocking_wait(self):
        limiter = RateLimiter(rate=10, per_seconds=0.1, burst=1)
        # 1st consume
        assert limiter.acquire(1.0, blocking=False) is True
        # 2nd with blocking=True and enough timeout
        t0 = time.monotonic()
        assert limiter.acquire(1.0, blocking=True, timeout=0.5) is True
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.008

    def test_rate_limiter_blocking_wait_no_timeout(self):
        limiter = RateLimiter(rate=20, per_seconds=0.05, burst=1)
        assert limiter.acquire(1.0, blocking=False) is True
        assert limiter.acquire(1.0, blocking=True, timeout=None) is True

    def test_rate_limiter_timeout_exceeded(self):
        limiter = RateLimiter(rate=1, per_seconds=10.0, burst=1)
        assert limiter.acquire(1.0, blocking=False) is True
        # Requesting 1 token needs 10 seconds, but timeout is 0.05s
        t0 = time.monotonic()
        assert limiter.acquire(1.0, blocking=True, timeout=0.05) is False
        elapsed = time.monotonic() - t0
        assert elapsed <= 0.2

    def test_rate_limiter_context_manager(self):
        limiter = RateLimiter(rate=5, per_seconds=0.1)
        with limiter as ok:
            assert ok is True

    def test_rate_limiter_decorator(self):
        limiter = RateLimiter(rate=5, per_seconds=0.1)

        @limiter
        def send_msg(msg):
            return f"sent: {msg}"

        assert send_msg("hello") == "sent: hello"

    @pytest.mark.asyncio
    async def test_rate_limiter_decorator_async(self):
        limiter = RateLimiter(rate=5, per_seconds=0.1)

        @limiter
        async def async_fetch():
            return "async_token_ok"

        assert await async_fetch() == "async_token_ok"

    def test_rate_limiter_exceed_burst_error(self):
        limiter = RateLimiter(rate=5, burst=5)
        with pytest.raises(ValueError, match="exceeds burst capacity"):
            limiter.acquire(tokens=10)

    def test_rate_limiter_invalid_params(self):
        with pytest.raises(ValueError, match="rate must be > 0"):
            RateLimiter(rate=0)
        with pytest.raises(ValueError, match="per_seconds must be > 0"):
            RateLimiter(rate=5, per_seconds=0)
        with pytest.raises(ValueError, match="burst must be > 0"):
            RateLimiter(rate=5, burst=-1)
        limiter = RateLimiter(rate=5)
        with pytest.raises(ValueError, match="tokens must be > 0"):
            limiter.acquire(tokens=0)
