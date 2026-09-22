"""quiver.collections: Modern, zero-dependency, immutable collection operations.

Provides functional, non-mutating primitives for slicing, grouping, flattening,
and querying nested mappings and sequences.
"""

from collections import deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
import itertools
from typing import Any, Callable, Hashable, Literal, Optional, TypeVar, Union, overload

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
D = TypeVar("D")

_MISSING = object()


def chunk(
    iterable: Iterable[T],
    size: int,
    step: Optional[int] = None,
) -> Iterator[list[T]]:
    """Divide an iterable into lists of maximum `size`.

    If `step` is provided, each subsequent chunk starts `step` items after
    the start of the previous chunk.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    if step is not None and step < 1:
        raise ValueError("step must be >= 1")
    if not hasattr(iterable, "__iter__"):
        raise TypeError("iterable must be an Iterable")

    effective_step = size if step is None else step
    it = iter(iterable)

    if effective_step == size:
        while True:
            batch = list(itertools.islice(it, size))
            if not batch:
                break
            yield batch
    elif effective_step > size:
        skip = effective_step - size
        while True:
            batch = list(itertools.islice(it, size))
            if not batch:
                break
            yield batch
            for _ in range(skip):
                if next(it, _MISSING) is _MISSING:
                    return
    else:
        # effective_step < size
        buf: deque[T] = deque()
        for item in it:
            buf.append(item)
            if len(buf) == size:
                yield list(buf)
                for _ in range(effective_step):
                    if buf:
                        buf.popleft()
        while buf:
            yield list(buf)
            for _ in range(effective_step):
                if buf:
                    buf.popleft()


def flatten(
    iterable: Iterable[Any],
    depth: Optional[int] = None,
) -> Iterator[Any]:
    """Recursively flatten nested iterables up to `depth`.

    `str`, `bytes`, `bytearray`, and `Mapping` are treated as atomic items
    and are not flattened. Raises ValueError if a circular reference is detected.
    """
    if depth is not None and depth < 0:
        raise ValueError("depth must be >= 0")
    if not hasattr(iterable, "__iter__") or isinstance(
        iterable, (str, bytes, bytearray, Mapping)
    ):
        raise TypeError("iterable must be an Iterable (and non-atomic)")

    visited_ids: set[int] = set()

    def _flatten_rec(current: Any, current_depth: int) -> Iterator[Any]:
        curr_id = id(current)
        if curr_id in visited_ids:
            raise ValueError("Circular reference detected")
        visited_ids.add(curr_id)
        try:
            for item in current:
                if isinstance(item, (str, bytes, bytearray, Mapping)):
                    yield item
                elif depth is not None and current_depth >= depth:
                    yield item
                elif hasattr(item, "__iter__"):
                    yield from _flatten_rec(item, current_depth + 1)
                else:
                    yield item
        finally:
            visited_ids.remove(curr_id)

    return _flatten_rec(iterable, 0)


def group_by(
    iterable: Iterable[T],
    key_fn: Callable[[T], K],
) -> dict[K, list[T]]:
    """Group elements of `iterable` into a dict of lists by `key_fn(item)`.

    Original encounter order within each bucket is preserved.
    """
    if not callable(key_fn):
        raise TypeError("key_fn must be callable")

    result: dict[K, list[T]] = {}
    for item in iterable:
        key = key_fn(item)
        try:
            hash(key)
        except TypeError as err:
            raise TypeError(f"Key {key!r} is unhashable") from err
        result.setdefault(key, []).append(item)
    return result


def key_by(
    iterable: Iterable[T],
    key_fn: Callable[[T], K],
) -> dict[K, T]:
    """Map elements by `key_fn(item)`.

    Duplicate keys are overwritten by later elements.
    """
    if not callable(key_fn):
        raise TypeError("key_fn must be callable")

    result: dict[K, T] = {}
    for item in iterable:
        key = key_fn(item)
        result[key] = item
    return result


def partition(
    predicate: Callable[[T], bool],
    iterable: Iterable[T],
) -> tuple[list[T], list[T]]:
    """Partition items into a tuple of (trues, falses) according to `predicate`."""
    if not callable(predicate):
        raise TypeError("predicate must be callable")

    trues: list[T] = []
    falses: list[T] = []
    for item in iterable:
        if predicate(item):
            trues.append(item)
        else:
            falses.append(item)
    return (trues, falses)


def uniq_by(
    iterable: Iterable[T],
    key_fn: Optional[Callable[[T], Any]] = None,
) -> list[T]:
    """Return unique items preserving first encounter order.

    Unhashable keys gracefully fall back to string representations without raising errors.
    """
    seen: set[Any] = set()
    result: list[T] = []

    for item in iterable:
        k = key_fn(item) if key_fn is not None else item
        try:
            marker = (0, k)
            hash(marker)
        except TypeError:
            marker = (1, repr(k))

        if marker not in seen:
            seen.add(marker)
            result.append(item)

    return result


def windowed(
    iterable: Iterable[T],
    size: int,
    step: int = 1,
    fill_value: Any = _MISSING,
) -> Iterator[tuple[Any, ...]]:
    """Create a sliding window of `size` elements advancing by `step`.

    If `fill_value` is specified, trailing incomplete windows are padded.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    if step < 1:
        raise ValueError("step must be >= 1")
    if not hasattr(iterable, "__iter__"):
        raise TypeError("iterable must be an Iterable")

    it = iter(iterable)
    buf: list[Any] = []

    for item in it:
        buf.append(item)
        if len(buf) == size:
            yield tuple(buf)
            buf = buf[step:]

    if buf and fill_value is not _MISSING:
        padded = list(buf) + [fill_value] * (size - len(buf))
        yield tuple(padded)


def deep_get(
    mapping: Mapping[str, Any],
    path: Union[str, Sequence[Union[str, int]]],
    default: Optional[D] = None,
    *,
    separator: str = ".",
) -> Union[Any, D]:
    """Safely traverse a nested mapping or sequence using a path string or sequence."""
    if path == "" or path == []:
        return mapping

    if isinstance(path, str):
        keys: list[Union[str, int]] = path.split(separator)
    else:
        keys = list(path)

    current: Any = mapping
    for key in keys:
        if isinstance(current, Mapping):
            if key in current:
                current = current[key]
            elif isinstance(key, str) and key.isdigit() and int(key) in current:
                current = current[int(key)]
            else:
                return default
        elif isinstance(current, (list, tuple)):
            try:
                idx = int(key)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return default
            except (ValueError, TypeError):
                return default
        else:
            return default

    return current


def deep_set(
    mapping: Mapping[str, Any],
    path: Union[str, Sequence[Union[str, int]]],
    value: Any,
    *,
    separator: str = ".",
) -> dict[str, Any]:
    """Set value at nested path returning a new dictionary (Copy-on-Write).

    Leaves original mapping completely untouched.
    """
    if isinstance(path, str):
        if not path:
            raise ValueError("path must not be empty")
        keys = path.split(separator)
    else:
        keys = list(path)
        if not keys:
            raise ValueError("path must not be empty")

    def _set_cow(curr: Any, remaining: list[Union[str, int]]) -> dict[str, Any]:
        k = str(remaining[0])
        rest = remaining[1:]
        base = dict(curr) if isinstance(curr, Mapping) else {}
        if not rest:
            base[k] = value
            return base
        sub = base.get(k)
        base[k] = _set_cow(sub, rest)
        return base

    return _set_cow(mapping, keys)


def deep_merge(
    *mappings: Mapping[K, V],
    deep: bool = True,
) -> dict[K, V]:
    """Recursively merge multiple dictionaries from left to right into a new dict."""
    if not mappings:
        return {}

    for idx, m in enumerate(mappings):
        if not isinstance(m, Mapping):
            raise TypeError(
                f"All arguments must be Mapping instances (got {type(m)} at index {idx})"
            )

    visited_ids: set[int] = set()

    def _merge_into(target: dict[Any, Any], source: Mapping[Any, Any]) -> None:
        src_id = id(source)
        if src_id in visited_ids:
            raise ValueError("Circular reference detected")
        visited_ids.add(src_id)
        try:
            for k, v in source.items():
                if deep and isinstance(v, Mapping) and isinstance(target.get(k), Mapping):
                    sub_target = dict(target[k])
                    _merge_into(sub_target, v)
                    target[k] = sub_target
                elif isinstance(v, Mapping):
                    sub = {}
                    _merge_into(sub, v)
                    target[k] = sub
                else:
                    target[k] = v
        finally:
            visited_ids.remove(src_id)

    result: dict[Any, Any] = {}
    for m in mappings:
        _merge_into(result, m)

    return result


def pick(mapping: Mapping[K, V], *keys: K) -> dict[K, V]:
    """Return a new dict with only the specified keys present in mapping."""
    return {k: mapping[k] for k in keys if k in mapping}


def omit(mapping: Mapping[K, V], *keys: K) -> dict[K, V]:
    """Return a new dict omitting the specified keys."""
    exclude = set(keys)
    return {k: v for k, v in mapping.items() if k not in exclude}


@overload
def invert(mapping: Mapping[K, V], *, multi: Literal[False] = False) -> dict[V, K]: ...
@overload
def invert(mapping: Mapping[K, V], *, multi: Literal[True]) -> dict[V, list[K]]: ...
def invert(
    mapping: Mapping[K, V],
    *,
    multi: bool = False,
) -> Union[dict[V, K], dict[V, list[K]]]:
    """Invert key-value pairs of a mapping."""
    if not multi:
        return {v: k for k, v in mapping.items()}

    result: dict[V, list[K]] = {}
    for k, v in mapping.items():
        result.setdefault(v, []).append(k)
    return result
