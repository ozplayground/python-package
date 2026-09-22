"""Tests for quiver.behavior module.

Covers pipe, compose, curry, once, debounce, throttle, memoize (TTL/LRU), retry (sync and async).
"""

import asyncio
import time
import threading
import pytest

from quiver.behavior import (
    compose,
    curry,
    debounce,
    memoize,
    once,
    pipe,
    retry,
    throttle,
)


# ==========================================
# 1. pipe tests
# ==========================================
class TestPipe:
    def test_pipe_chain(self):
        result = pipe(
            5,
            lambda x: x * 2,
            lambda x: x + 10,
            str,
        )
        assert result == "20"

    def test_pipe_no_functions(self):
        assert pipe(42) == 42

    def test_pipe_non_callable_error(self):
        with pytest.raises(TypeError, match="All functions passed to pipe must be callable"):
            pipe(10, lambda x: x * 2, "not_callable")  # type: ignore


# ==========================================
# 2. compose tests
# ==========================================
class TestCompose:
    def test_compose_chain(self):
        fn = compose(
            str,
            lambda x: x + 10,
            lambda x: x * 2,
        )
        assert fn(5) == "20"

    def test_compose_multiple_arguments(self):
        fn = compose(
            lambda x: x * 2,
            lambda a, b: a + b,
        )
        assert fn(3, 4) == 14

    def test_compose_empty(self):
        identity = compose()
        assert identity(123) == 123

    def test_compose_non_callable_error(self):
        with pytest.raises(TypeError, match="All arguments to compose must be callable"):
            compose(lambda x: x, 123)  # type: ignore


# ==========================================
# 3. curry tests
# ==========================================
class TestCurry:
    def test_curry_basic(self):
        def add3(a, b, c):
            return a + b + c

        curried = curry(add3)
        assert curried(1)(2)(3) == 6
        assert curried(1, 2)(3) == 6
        assert curried(1)(2, 3) == 6
        assert curried(1, 2, 3) == 6

    def test_curry_with_kwargs(self):
        def greet(greeting, name, punct="!"):
            return f"{greeting}, {name}{punct}"

        c_greet = curry(greet, arity=2)
        assert c_greet("Hello")("Alice") == "Hello, Alice!"
        assert c_greet("Hi")("Bob", punct=".") == "Hi, Bob."

    def test_curry_explicit_arity(self):
        def varargs(*args):
            return sum(args)

        curried = curry(varargs, arity=3)
        assert curried(10)(20)(30) == 60

    def test_curry_varargs_without_arity_error(self):
        def varargs(*args):
            return sum(args)

        with pytest.raises(ValueError, match="Cannot determine arity"):
            curry(varargs)


# ==========================================
# 4. once tests
# ==========================================
class TestOnce:
    def test_once_executes_only_first_time(self):
        call_count = 0

        @once
        def initialize(x):
            nonlocal call_count
            call_count += 1
            return x * 10

        assert initialize(5) == 50
        assert initialize(100) == 50
        assert call_count == 1

    def test_once_reset(self):
        call_count = 0

        @once
        def counter():
            nonlocal call_count
            call_count += 1
            return call_count

        assert counter() == 1
        assert counter() == 1
        counter.reset()
        assert counter() == 2
        assert counter() == 2

    def test_once_error_not_cached(self):
        attempt = 0

        @once
        def flaky():
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise RuntimeError("First attempt failed")
            return "success"

        with pytest.raises(RuntimeError, match="First attempt failed"):
            flaky()

        # Subsequent call should succeed and not be locked into error
        assert flaky() == "success"
        assert flaky() == "success"
        assert attempt == 2


# ==========================================
# 5. debounce tests
# ==========================================
class TestDebounce:
    def test_debounce_delays_execution(self):
        executed = []

        @debounce(wait_seconds=0.05)
        def record(val):
            executed.append(val)

        record(1)
        record(2)
        record(3)
        assert executed == []

        time.sleep(0.08)
        assert executed == [3]

    def test_debounce_cancel(self):
        executed = []

        @debounce(wait_seconds=0.05)
        def record(val):
            executed.append(val)

        record(1)
        record.cancel()
        time.sleep(0.08)
        assert executed == []

    def test_debounce_flush(self):
        executed = []

        @debounce(wait_seconds=0.5)
        def record(val):
            executed.append(val)

        record(42)
        assert executed == []
        record.flush()
        assert executed == [42]

    def test_debounce_invalid_wait(self):
        with pytest.raises(ValueError, match="wait_seconds must be > 0"):
            debounce(wait_seconds=0)


# ==========================================
# 6. throttle tests
# ==========================================
class TestThrottle:
    def test_throttle_limits_rate(self):
        call_count = 0

        @throttle(interval_seconds=0.05)
        def ping():
            nonlocal call_count
            call_count += 1
            return call_count

        # 1st call executes immediately
        res1 = ping()
        assert res1 == 1

        # 2nd call within 0.05s is suppressed (returns None)
        res2 = ping()
        assert res2 is None
        assert call_count == 1

        # After interval, executes again
        time.sleep(0.06)
        res3 = ping()
        assert res3 == 2
        assert call_count == 2

    def test_throttle_invalid_interval(self):
        with pytest.raises(ValueError, match="interval_seconds must be > 0"):
            throttle(interval_seconds=-1)


# ==========================================
# 7. memoize tests
# ==========================================
class TestMemoize:
    def test_memoize_basic(self):
        calls = 0

        @memoize()
        def square(x):
            nonlocal calls
            calls += 1
            return x * x

        assert square(4) == 16
        assert square(4) == 16
        assert calls == 1
        assert square(5) == 25
        assert calls == 2

    def test_memoize_ttl(self):
        calls = 0

        @memoize(ttl_seconds=0.04)
        def get_data(k):
            nonlocal calls
            calls += 1
            return f"val_{k}_{calls}"

        v1 = get_data("a")
        assert v1 == "val_a_1"
        assert get_data("a") == "val_a_1"
        assert calls == 1

        time.sleep(0.06)
        v2 = get_data("a")
        assert v2 == "val_a_2"
        assert calls == 2

    def test_memoize_lru_maxsize(self):
        @memoize(maxsize=2)
        def fn(x):
            return x * 10

        fn(1)
        fn(2)
        info = fn.cache_info()
        assert info["currsize"] == 2

        fn(3)  # Evicts 1
        info = fn.cache_info()
        assert info["currsize"] == 2

        # fn(1) should be a miss now
        fn(1)
        info = fn.cache_info()
        assert info["misses"] >= 4

    def test_memoize_unhashable_args_fallback(self):
        calls = 0

        @memoize()
        def process_dict(d):
            nonlocal calls
            calls += 1
            return sum(d.values())

        d1 = {"a": 1, "b": 2}
        assert process_dict(d1) == 3
        assert process_dict(d1) == 3
        assert calls == 1

    def test_memoize_reentrant_recursion(self):
        calls = 0

        @memoize()
        def fib(n):
            nonlocal calls
            calls += 1
            if n <= 1:
                return n
            return fib(n - 1) + fib(n - 2)

        assert fib(10) == 55
        assert calls == 11  # 0 to 10 computed once each

    def test_memoize_custom_key_fn(self):
        @memoize(key_fn=lambda a, b: f"{a}:{b}")
        def concat(a, b):
            return f"{a}_{b}"

        assert concat("x", "y") == "x_y"

    def test_memoize_cache_clear(self):
        calls = 0

        @memoize()
        def fetch(x):
            nonlocal calls
            calls += 1
            return x

        fetch(1)
        assert calls == 1
        fetch.cache_clear()
        assert fetch.cache_info()["currsize"] == 0
        fetch(1)
        assert calls == 2


# ==========================================
# 8. retry tests (Sync and Async)
# ==========================================
class TestRetry:
    def test_retry_propagates_keyboard_interrupt(self):
        @retry(max_attempts=3)
        def interrupt():
            raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            interrupt()

    @pytest.mark.asyncio
    async def test_retry_async_propagates_system_exit(self):
        @retry(max_attempts=3)
        async def sys_exit():
            raise SystemExit()

        with pytest.raises(SystemExit):
            await sys_exit()

    def test_retry_sync_success_first_try(self):
        calls = 0

        @retry(max_attempts=3, backoff_base=0.01)
        def succeed():
            nonlocal calls
            calls += 1
            return "ok"

        assert succeed() == "ok"
        assert calls == 1

    def test_retry_sync_eventual_success(self):
        attempts = 0
        logged_retries = []

        def on_retry(exc, attempt, wait_time):
            logged_retries.append((type(exc), attempt, wait_time))

        @retry(
            max_attempts=4,
            backoff_base=0.01,
            jitter=False,
            exceptions=(ValueError,),
            on_retry=on_retry,
        )
        def fail_twice():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("temporary error")
            return "recovered"

        assert fail_twice() == "recovered"
        assert attempts == 3
        assert len(logged_retries) == 2

    def test_retry_sync_exceeds_max_attempts(self):
        attempts = 0

        @retry(max_attempts=3, backoff_base=0.01, jitter=False)
        def always_fail():
            nonlocal attempts
            attempts += 1
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            always_fail()
        assert attempts == 3

    def test_retry_non_matching_exception_raises_immediately(self):
        attempts = 0

        @retry(max_attempts=5, backoff_base=0.01, exceptions=(ValueError,))
        def raise_type_error():
            nonlocal attempts
            attempts += 1
            raise TypeError("unexpected")

        with pytest.raises(TypeError, match="unexpected"):
            raise_type_error()
        assert attempts == 1

    @pytest.mark.asyncio
    async def test_retry_async_eventual_success(self):
        attempts = 0

        @retry(max_attempts=3, backoff_base=0.01, jitter=False)
        async def async_fetch():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("connection lost")
            return "async_ok"

        result = await async_fetch()
        assert result == "async_ok"
        assert attempts == 2

    def test_retry_invalid_parameters(self):
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            retry(max_attempts=0)
        with pytest.raises(ValueError, match="backoff_base must be > 0"):
            retry(backoff_base=-0.5)
        with pytest.raises(ValueError, match="backoff_max must be >= backoff_base"):
            retry(backoff_base=10.0, backoff_max=5.0)
