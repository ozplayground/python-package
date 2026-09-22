"""quiver.scope: Kotlin-inspired scope functions and null-safety chaining utilities.

Provides functional scope combinators: let, also, tap, take_if, take_unless, and coalesce.
"""

from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def let(target: T, block: Callable[[T], R]) -> R:
    """Transform `target` using `block(target)` and return the block's result."""
    if not callable(block):
        raise TypeError("block must be callable")
    return block(target)


def also(target: T, block: Callable[[T], Any]) -> T:
    """Execute side effect `block(target)` and return the unchanged `target` (identity guaranteed)."""
    if not callable(block):
        raise TypeError("block must be callable")
    block(target)
    return target


def tap(target: T, block: Callable[[T], Any]) -> T:
    """Alias for `also`. Execute side effect `block(target)` and return `target`."""
    return also(target, block)


def take_if(target: T, predicate: Callable[[T], bool]) -> Optional[T]:
    """Return `target` if `predicate(target)` is True, otherwise return None."""
    if not callable(predicate):
        raise TypeError("predicate must be callable")
    return target if predicate(target) else None


def take_unless(target: T, predicate: Callable[[T], bool]) -> Optional[T]:
    """Return None if `predicate(target)` is True, otherwise return `target`."""
    if not callable(predicate):
        raise TypeError("predicate must be callable")
    return None if predicate(target) else target


def coalesce(*values: Optional[T], default: Optional[T] = None) -> Optional[T]:
    """Return the first value that is not None, or `default` if all values are None."""
    for v in values:
        if v is not None:
            return v
    return default
