"""Tests for quiver.scope module.

Covers let, also, tap, take_if, take_unless, and coalesce.
"""

import pytest

from quiver.scope import (
    also,
    coalesce,
    let,
    take_if,
    take_unless,
    tap,
)


# ==========================================
# 1. let tests
# ==========================================
class TestLet:
    def test_let_transforms_value(self):
        result = let("hello", lambda s: s.upper() + "!")
        assert result == "HELLO!"

    def test_let_with_none_target(self):
        result = let(None, lambda x: "was_none" if x is None else "not_none")
        assert result == "was_none"

    def test_let_not_callable_error(self):
        with pytest.raises(TypeError, match="block must be callable"):
            let("value", "not_callable")  # type: ignore


# ==========================================
# 2. also and tap tests
# ==========================================
class TestAlsoAndTap:
    def test_also_executes_side_effect_and_returns_target(self):
        side_effects = []
        data = {"count": 0}

        ret = also(data, lambda d: (d.update({"count": 1}), side_effects.append("done")))
        assert ret is data  # strict identity check
        assert ret["count"] == 1
        assert side_effects == ["done"]

    def test_tap_identical_to_also(self):
        side_effects = []
        obj = [1, 2, 3]

        ret = tap(obj, lambda x: side_effects.append(len(x)))
        assert ret is obj
        assert side_effects == [3]

    def test_also_not_callable_error(self):
        with pytest.raises(TypeError, match="block must be callable"):
            also(123, "not_callable")  # type: ignore

    def test_tap_not_callable_error(self):
        with pytest.raises(TypeError, match="block must be callable"):
            tap(123, "not_callable")  # type: ignore


# ==========================================
# 3. take_if and take_unless tests
# ==========================================
class TestTakeIfAndUnless:
    def test_take_if_true_returns_target(self):
        assert take_if(10, lambda x: x > 5) == 10
        assert take_if("hello", lambda s: len(s) > 3) == "hello"

    def test_take_if_false_returns_none(self):
        assert take_if(3, lambda x: x > 5) is None
        assert take_if("", lambda s: len(s) > 0) is None

    def test_take_unless_true_returns_none(self):
        assert take_unless(10, lambda x: x > 5) is None
        assert take_unless("error", lambda s: "err" in s) is None

    def test_take_unless_false_returns_target(self):
        assert take_unless(3, lambda x: x > 5) == 3
        assert take_unless("ok", lambda s: "err" in s) == "ok"

    def test_take_if_not_callable_error(self):
        with pytest.raises(TypeError, match="predicate must be callable"):
            take_if(10, "not_callable")  # type: ignore

    def test_take_unless_not_callable_error(self):
        with pytest.raises(TypeError, match="predicate must be callable"):
            take_unless(10, "not_callable")  # type: ignore


# ==========================================
# 4. coalesce tests
# ==========================================
class TestCoalesce:
    def test_coalesce_first_non_none(self):
        assert coalesce(None, None, "found", "ignored") == "found"
        assert coalesce("first", None) == "first"

    def test_coalesce_preserves_falsy_values(self):
        # 0, "", False, [] are valid non-None values and should be preserved
        assert coalesce(None, 0, 100) == 0
        assert coalesce(None, "", "default") == ""
        assert coalesce(None, False, True) is False
        assert coalesce(None, [], [1, 2]) == []

    def test_coalesce_all_none_returns_default(self):
        assert coalesce(None, None) is None
        assert coalesce(None, None, default="fallback") == "fallback"
        assert coalesce(default="fallback") == "fallback"
