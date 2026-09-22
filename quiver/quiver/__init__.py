"""Quiver: The Modern, Zero-Dependency, Fully Type-Safe Utility Quiver for Python Engineers."""

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
from quiver.collections import (
    chunk,
    deep_get,
    deep_merge,
    deep_set,
    flatten,
    group_by,
    invert,
    key_by,
    omit,
    partition,
    pick,
    uniq_by,
    windowed,
)
from quiver.scope import (
    also,
    coalesce,
    let,
    take_if,
    take_unless,
    tap,
)
from quiver.strings import (
    mask_sensitive,
    slugify,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
    truncate,
)
from quiver.timing import (
    RateLimiter,
    Stopwatch,
    measure_time,
)

__all__ = [
    # Collections
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
    # Behavior
    "pipe",
    "compose",
    "curry",
    "once",
    "debounce",
    "throttle",
    "memoize",
    "retry",
    # Strings
    "to_camel_case",
    "to_snake_case",
    "to_kebab_case",
    "to_pascal_case",
    "slugify",
    "truncate",
    "mask_sensitive",
    # Scope
    "let",
    "also",
    "tap",
    "take_if",
    "take_unless",
    "coalesce",
    # Timing
    "Stopwatch",
    "measure_time",
    "RateLimiter",
]
