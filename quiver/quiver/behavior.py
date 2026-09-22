"""quiver.behavior: Higher-order functions, function composition, and execution control.

Provides decorators and combinators for piping, currying, once-only execution,
debouncing, throttling, memoization with TTL/LRU, and exponential backoff retry.
"""

from collections import OrderedDict
import functools
import inspect
import random
import threading
import time
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

P = ParamSpec("P")
R = TypeVar("R")


def pipe(value: Any, *fns: Callable[[Any], Any]) -> Any:
    """Pass `value` through a left-to-right chain of functions: f1(val) -> f2(...) -> ..."""
    for idx, fn in enumerate(fns):
        if not callable(fn):
            raise TypeError(
                f"All functions passed to pipe must be callable (got {type(fn)} at index {idx})"
            )
    result = value
    for fn in fns:
        result = fn(result)
    return result


def compose(*fns: Callable[[Any], Any]) -> Callable[..., Any]:
    """Compose functions right-to-left: compose(f, g, h)(x) == f(g(h(x)))."""
    for idx, fn in enumerate(fns):
        if not callable(fn):
            raise TypeError(
                f"All arguments to compose must be callable (got {type(fn)} at index {idx})"
            )

    if not fns:
        return lambda x: x

    @functools.wraps(fns[0])
    def composed(*args: Any, **kwargs: Any) -> Any:
        res = fns[-1](*args, **kwargs)
        for fn in reversed(fns[:-1]):
            res = fn(res)
        return res

    return composed


def curry(
    fn: Callable[..., R],
    arity: Optional[int] = None,
) -> Callable[..., Any]:
    """Curry a multi-argument function into a chain of single/multi argument applications."""
    if not callable(fn):
        raise TypeError("fn must be callable")

    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    has_varargs = any(
        p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for p in params
    )
    pos_params = [
        p
        for p in params
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]

    if has_varargs and not pos_params and arity is None:
        raise ValueError("Cannot determine arity of varargs function without explicit arity")

    target_arity = len(pos_params) if arity is None else arity

    def _make_curried(accum_args: tuple[Any, ...], accum_kwargs: dict[str, Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def _curried_step(*args: Any, **kwargs: Any) -> Any:
            new_args = accum_args + args
            new_kwargs = {**accum_kwargs, **kwargs}
            if len(new_args) >= target_arity:
                return fn(*new_args, **new_kwargs)
            return _make_curried(new_args, new_kwargs)

        return _curried_step

    return _make_curried((), {})


class OnceWrapper(Generic[P, R]):
    """Wrapper ensuring a callable runs at most once in a multi-threaded environment."""

    def __init__(self, fn: Callable[P, R]) -> None:
        self._fn = fn
        self._has_run = False
        self._result: Optional[R] = None
        self._lock = threading.Lock()
        functools.update_wrapper(self, fn)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        if not self._has_run:
            with self._lock:
                if not self._has_run:
                    self._result = self._fn(*args, **kwargs)
                    self._has_run = True
        return self._result  # type: ignore

    def reset(self) -> None:
        """Reset execution state to allow running again."""
        with self._lock:
            self._has_run = False
            self._result = None


def once(fn: Callable[P, R]) -> OnceWrapper[P, R]:
    """Decorator guaranteeing idempotent single-execution via Double-Checked Locking."""
    return OnceWrapper(fn)


class DebounceWrapper(Generic[P, R]):
    """Wrapper delaying execution until a period of silence has elapsed."""

    def __init__(self, fn: Callable[P, R], wait_seconds: float) -> None:
        self._fn = fn
        self._wait_seconds = wait_seconds
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._latest_args: tuple[Any, ...] = ()
        self._latest_kwargs: dict[str, Any] = {}
        functools.update_wrapper(self, fn)

    def _execute(self) -> None:
        with self._lock:
            args = self._latest_args
            kwargs = self._latest_kwargs
            self._timer = None
        self._fn(*args, **kwargs)  # type: ignore

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        with self._lock:
            self._latest_args = args
            self._latest_kwargs = kwargs
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._wait_seconds, self._execute)
            self._timer.daemon = True
            self._timer.start()

    def cancel(self) -> None:
        """Cancel any scheduled delayed execution."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def flush(self) -> None:
        """Execute immediately if an execution is currently scheduled."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
                args = self._latest_args
                kwargs = self._latest_kwargs
            else:
                return
        self._fn(*args, **kwargs)  # type: ignore


def debounce(wait_seconds: float) -> Callable[[Callable[P, R]], DebounceWrapper[P, R]]:
    """Decorator delaying execution until `wait_seconds` have passed since the last call."""
    if wait_seconds <= 0:
        raise ValueError("wait_seconds must be > 0")

    def _decorator(fn: Callable[P, R]) -> DebounceWrapper[P, R]:
        return DebounceWrapper(fn, wait_seconds)

    return _decorator


class ThrottleWrapper(Generic[P, R]):
    """Wrapper restricting execution frequency to at most once per interval."""

    def __init__(self, fn: Callable[P, R], interval_seconds: float) -> None:
        self._fn = fn
        self._interval_seconds = interval_seconds
        self._last_called_time: float = -float("inf")
        self._lock = threading.Lock()
        functools.update_wrapper(self, fn)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Optional[R]:
        with self._lock:
            now = time.monotonic()
            if now - self._last_called_time >= self._interval_seconds:
                self._last_called_time = now
                should_execute = True
            else:
                should_execute = False

        if should_execute:
            return self._fn(*args, **kwargs)
        return None


def throttle(interval_seconds: float) -> Callable[[Callable[P, R]], ThrottleWrapper[P, R]]:
    """Decorator limiting call frequency to at most once per `interval_seconds`."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be > 0")

    def _decorator(fn: Callable[P, R]) -> ThrottleWrapper[P, R]:
        return ThrottleWrapper(fn, interval_seconds)

    return _decorator


class _CacheEntry:
    __slots__ = ("value", "expire_at")

    def __init__(self, value: Any, expire_at: Optional[float]) -> None:
        self.value = value
        self.expire_at = expire_at


class MemoizeWrapper(Generic[P, R]):
    """Thread-safe memoization wrapper supporting TTL and LRU cache eviction."""

    def __init__(
        self,
        fn: Callable[P, R],
        ttl_seconds: Optional[float],
        maxsize: Optional[int],
        key_fn: Optional[Callable[..., Any]],
    ) -> None:
        self._fn = fn
        self._ttl_seconds = ttl_seconds
        self._maxsize = maxsize
        self._key_fn = key_fn
        self._cache: OrderedDict[Any, _CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        functools.update_wrapper(self, fn)

    def _make_key(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        if self._key_fn is not None:
            return self._key_fn(*args, **kwargs)

        def _norm(x: Any) -> Any:
            try:
                hash(x)
                return x
            except TypeError:
                return repr(x)

        norm_args = tuple(_norm(a) for a in args)
        norm_kwargs = tuple(sorted((k, _norm(v)) for k, v in kwargs.items()))
        return (norm_args, norm_kwargs)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        key = self._make_key(args, kwargs)
        with self._lock:
            now = time.monotonic()
            if key in self._cache:
                entry = self._cache[key]
                if entry.expire_at is None or now < entry.expire_at:
                    self._hits += 1
                    self._cache.move_to_end(key)
                    return entry.value
                else:
                    del self._cache[key]

            self._misses += 1
            result = self._fn(*args, **kwargs)
            expire_at = now + self._ttl_seconds if self._ttl_seconds is not None else None

            if self._maxsize is not None and len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)

            self._cache[key] = _CacheEntry(result, expire_at)
            return result

    def cache_clear(self) -> None:
        """Clear all entries in the cache and reset counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cache_info(self) -> dict[str, Any]:
        """Return cache hit, miss, and size statistics."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "currsize": len(self._cache),
                "maxsize": self._maxsize,
            }


def memoize(
    ttl_seconds: Optional[float] = None,
    maxsize: Optional[int] = 128,
    key_fn: Optional[Callable[..., Any]] = None,
) -> Callable[[Callable[P, R]], MemoizeWrapper[P, R]]:
    """Decorator providing thread-safe TTL and LRU memoization."""

    def _decorator(fn: Callable[P, R]) -> MemoizeWrapper[P, R]:
        return MemoizeWrapper(fn, ttl_seconds, maxsize, key_fn)

    return _decorator


def retry(
    max_attempts: int = 3,
    backoff_base: float = 0.5,
    backoff_max: float = 60.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Smart exponential backoff retry decorator with Full Jitter for sync and async functions."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if backoff_base <= 0:
        raise ValueError("backoff_base must be > 0")
    if backoff_max < backoff_base:
        raise ValueError("backoff_max must be >= backoff_base")

    def _calc_wait(attempt: int) -> float:
        temp = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
        return random.uniform(0, temp) if jitter else temp

    def _decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(fn):
            import asyncio

            @functools.wraps(fn)
            async def _async_retry(*args: P.args, **kwargs: P.kwargs) -> R:
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await fn(*args, **kwargs)  # type: ignore
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except exceptions as exc:
                        if attempt >= max_attempts:
                            raise
                        wait_time = _calc_wait(attempt)
                        if on_retry is not None:
                            on_retry(exc, attempt, wait_time)
                        await asyncio.sleep(wait_time)
                raise RuntimeError("Exhausted retries")

            return _async_retry  # type: ignore
        else:
            @functools.wraps(fn)
            def _sync_retry(*args: P.args, **kwargs: P.kwargs) -> R:
                for attempt in range(1, max_attempts + 1):
                    try:
                        return fn(*args, **kwargs)
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except exceptions as exc:
                        if attempt >= max_attempts:
                            raise
                        wait_time = _calc_wait(attempt)
                        if on_retry is not None:
                            on_retry(exc, attempt, wait_time)
                        time.sleep(wait_time)
                raise RuntimeError("Exhausted retries")

            return _sync_retry

    return _decorator
