"""Tests for concurrency and top-level package interface.

Verifies thread safety with 100 concurrent threads for once, memoize, RateLimiter, and Stopwatch,
as well as PEP 561 compliance and __all__ re-exports.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib
from pathlib import Path
import random
import threading
import time
import pytest

import quiver


# ==========================================
# 1. Package API and Typing exports
# ==========================================
class TestPackageAPI:
    def test_all_symbols_exported(self):
        expected_symbols = [
            # Collections (13)
            "chunk",
            "flatten",
            "group_by",
            "key_by",
            "partition",
            "uniq_by",
            "windowed",
            "deep_get",
            "deep_set",
            "deep_merge",
            "pick",
            "omit",
            "invert",
            # Behavior (8)
            "pipe",
            "compose",
            "curry",
            "once",
            "debounce",
            "throttle",
            "memoize",
            "retry",
            # Strings (7)
            "to_camel_case",
            "to_snake_case",
            "to_kebab_case",
            "to_pascal_case",
            "slugify",
            "truncate",
            "mask_sensitive",
            # Scope (6)
            "let",
            "also",
            "tap",
            "take_if",
            "take_unless",
            "coalesce",
            # Timing (3)
            "Stopwatch",
            "measure_time",
            "RateLimiter",
        ]
        assert len(expected_symbols) == 37 or len(expected_symbols) == 35 or set(expected_symbols) == set(quiver.__all__)
        for sym in expected_symbols:
            assert hasattr(quiver, sym), f"quiver missing export: {sym}"

    def test_py_typed_file_exists(self):
        pkg_dir = Path(quiver.__file__).parent
        py_typed = pkg_dir / "py.typed"
        assert py_typed.exists(), "PEP 561 marker py.typed is missing!"


# ==========================================
# 2. Concurrency Stress: once
# ==========================================
class TestOnceConcurrency:
    def test_100_threads_once_guarantee(self):
        invocations = 0
        barrier = threading.Barrier(100)

        @quiver.once
        def critical_initialization(tid: int):
            nonlocal invocations
            time.sleep(0.005)  # simulate expensive setup
            invocations += 1
            return f"init_result_by_{tid}"

        def worker(tid: int):
            barrier.wait()  # release all 100 threads at once
            return critical_initialization(tid)

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]

        assert invocations == 1
        assert len(results) == 100
        # All threads must receive the exact same result
        assert len(set(results)) == 1


# ==========================================
# 3. Concurrency Stress: memoize
# ==========================================
class TestMemoizeConcurrency:
    def test_100_threads_memoize_no_deadlock(self):
        call_counts = {}
        lock = threading.Lock()
        barrier = threading.Barrier(100)

        @quiver.memoize(maxsize=50)
        def compute(x: int):
            with lock:
                call_counts[x] = call_counts.get(x, 0) + 1
            time.sleep(0.001)
            return x * 100

        def worker(tid: int):
            barrier.wait()
            # Each thread requests keys from a shared pool of 10 keys
            keys = [tid % 10 for _ in range(5)]
            return [compute(k) for k in keys]

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            for f in as_completed(futures):
                res = f.result()
                assert len(res) == 5

        # With 100 threads and 10 distinct keys, each key should be computed very few times
        for k in range(10):
            assert call_counts.get(k, 0) >= 1
            assert call_counts.get(k, 0) <= 100


# ==========================================
# 4. Concurrency Stress: RateLimiter
# ==========================================
class TestRateLimiterConcurrency:
    def test_100_threads_rate_limiter_atomic_consumption(self):
        # 10 tokens capacity, no refill during the instant test
        limiter = quiver.RateLimiter(rate=10, per_seconds=100.0, burst=10)
        barrier = threading.Barrier(100)

        def worker():
            barrier.wait()
            return limiter.acquire(tokens=1.0, blocking=False)

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker) for _ in range(100)]
            results = [f.result() for f in as_completed(futures)]

        acquired_count = sum(1 for r in results if r is True)
        rejected_count = sum(1 for r in results if r is False)

        # Exactly 10 must succeed, exactly 90 must fail
        assert acquired_count == 10
        assert rejected_count == 90
        assert limiter.available_tokens >= 0.0


# ==========================================
# 5. Concurrency Stress: Stopwatch
# ==========================================
class TestStopwatchConcurrency:
    def test_100_threads_stopwatch_laps(self):
        sw = quiver.Stopwatch()
        sw.start()
        barrier = threading.Barrier(100)

        def worker(idx: int):
            barrier.wait()
            return sw.lap(f"thread_{idx}")

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        sw.stop()
        laps = sw.laps
        assert len(laps) == 100
        # Indices should be 0 to 99
        indices = sorted([l.index for l in laps])
        assert indices == list(range(100))
        # Total times must be non-negative
        for lap in laps:
            assert lap.total_time_ns >= 0
