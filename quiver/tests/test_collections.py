"""Tests for quiver.collections module.

Covers normal, boundary, error cases, and immutability guarantees.
"""

from collections.abc import Mapping
import pytest

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


# ==========================================
# 1. chunk tests
# ==========================================
class TestChunk:
    def test_chunk_normal(self):
        items = [1, 2, 3, 4, 5]
        result = list(chunk(items, 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_chunk_with_step(self):
        items = [1, 2, 3, 4, 5]
        result = list(chunk(items, 2, step=1))
        assert result == [[1, 2], [2, 3], [3, 4], [4, 5], [5]]

    def test_chunk_with_larger_step(self):
        items = [1, 2, 3, 4, 5, 6]
        result = list(chunk(items, 2, step=3))
        assert result == [[1, 2], [4, 5]]

    def test_chunk_step_larger_than_size_exhaustion(self):
        assert list(chunk([1, 2], size=2, step=4)) == [[1, 2]]

    def test_chunk_empty_iterable(self):
        assert list(chunk([], 3)) == []

    def test_chunk_generator_input(self):
        gen = (x for x in range(5))
        assert list(chunk(gen, 3)) == [[0, 1, 2], [3, 4]]

    def test_chunk_invalid_size(self):
        with pytest.raises(ValueError, match="size must be >= 1"):
            list(chunk([1, 2], 0))
        with pytest.raises(ValueError, match="size must be >= 1"):
            list(chunk([1, 2], -1))

    def test_chunk_invalid_step(self):
        with pytest.raises(ValueError, match="step must be >= 1"):
            list(chunk([1, 2], 2, step=0))

    def test_chunk_invalid_type(self):
        with pytest.raises(TypeError):
            list(chunk(12345, 2))  # type: ignore


# ==========================================
# 2. flatten tests
# ==========================================
class TestFlatten:
    def test_flatten_normal_deep(self):
        nested = [1, [2, [3, 4], 5], [[6]]]
        assert list(flatten(nested)) == [1, 2, 3, 4, 5, 6]

    def test_flatten_depth_limited(self):
        nested = [1, [2, [3, [4]]]]
        assert list(flatten(nested, depth=1)) == [1, 2, [3, [4]]]
        assert list(flatten(nested, depth=2)) == [1, 2, 3, [4]]
        assert list(flatten(nested, depth=0)) == [1, [2, [3, [4]]]]

    def test_flatten_atom_types_preserved(self):
        # str, bytes, bytearray, Mapping must NOT be flattened
        data = ["hello", b"world", {"a": 1, "b": 2}, [10, "nested"]]
        result = list(flatten(data))
        assert result == ["hello", b"world", {"a": 1, "b": 2}, 10, "nested"]

    def test_flatten_empty(self):
        assert list(flatten([])) == []

    def test_flatten_negative_depth_error(self):
        with pytest.raises(ValueError, match="depth must be >= 0"):
            list(flatten([1, 2], depth=-1))

    def test_flatten_cyclic_reference_error(self):
        cyclic_list: list = [1, 2]
        cyclic_list.append(cyclic_list)
        with pytest.raises(ValueError, match="Circular reference detected"):
            list(flatten(cyclic_list))

    def test_flatten_invalid_type(self):
        with pytest.raises(TypeError):
            list(flatten(100))  # type: ignore


# ==========================================
# 3. group_by tests
# ==========================================
class TestGroupBy:
    def test_group_by_normal(self):
        items = ["apple", "banana", "avocado", "cherry", "blueberry"]
        grouped = group_by(items, key_fn=lambda s: s[0])
        assert grouped == {
            "a": ["apple", "avocado"],
            "b": ["banana", "blueberry"],
            "c": ["cherry"],
        }

    def test_group_by_empty(self):
        assert group_by([], key_fn=lambda x: x) == {}

    def test_group_by_order_preserved(self):
        items = [{"id": 1, "g": "A"}, {"id": 2, "g": "B"}, {"id": 3, "g": "A"}]
        grouped = group_by(items, key_fn=lambda x: x["g"])
        assert [x["id"] for x in grouped["A"]] == [1, 3]
        assert [x["id"] for x in grouped["B"]] == [2]

    def test_group_by_not_callable(self):
        with pytest.raises(TypeError):
            group_by([1, 2], key_fn="not_callable")  # type: ignore

    def test_group_by_unhashable_key(self):
        with pytest.raises(TypeError):
            group_by([1, 2], key_fn=lambda x: [x])  # list is unhashable


# ==========================================
# 4. key_by tests
# ==========================================
class TestKeyBy:
    def test_key_by_normal(self):
        items = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = key_by(items, key_fn=lambda x: x["id"])
        assert result == {
            1: {"id": 1, "name": "Alice"},
            2: {"id": 2, "name": "Bob"},
        }

    def test_key_by_duplicate_overwrites(self):
        items = [{"id": 1, "val": "first"}, {"id": 1, "val": "second"}]
        result = key_by(items, key_fn=lambda x: x["id"])
        assert result == {1: {"id": 1, "val": "second"}}

    def test_key_by_empty(self):
        assert key_by([], key_fn=lambda x: x) == {}

    def test_key_by_not_callable(self):
        with pytest.raises(TypeError):
            key_by([1, 2], key_fn=None)  # type: ignore


# ==========================================
# 5. partition tests
# ==========================================
class TestPartition:
    def test_partition_normal(self):
        numbers = [1, 2, 3, 4, 5, 6]
        evens, odds = partition(lambda n: n % 2 == 0, numbers)
        assert evens == [2, 4, 6]
        assert odds == [1, 3, 5]

    def test_partition_all_true_or_all_false(self):
        evens, odds = partition(lambda n: n % 2 == 0, [2, 4, 6])
        assert evens == [2, 4, 6]
        assert odds == []

        evens, odds = partition(lambda n: n % 2 == 0, [1, 3, 5])
        assert evens == []
        assert odds == [1, 3, 5]

    def test_partition_empty(self):
        trues, falses = partition(lambda x: True, [])
        assert trues == []
        assert falses == []

    def test_partition_not_callable(self):
        with pytest.raises(TypeError):
            partition(123, [1, 2])  # type: ignore


# ==========================================
# 6. uniq_by tests
# ==========================================
class TestUniqBy:
    def test_uniq_by_default_identity(self):
        items = [1, 2, 2, 3, 1, 4, 3]
        assert uniq_by(items) == [1, 2, 3, 4]

    def test_uniq_by_custom_key_fn(self):
        items = ["apple", "apricot", "banana", "avocado", "berry"]
        # keep first item for each first letter
        result = uniq_by(items, key_fn=lambda s: s[0])
        assert result == ["apple", "banana"]

    def test_uniq_by_unhashable_items_fallback(self):
        # list of dicts: unhashable, should safely fallback without raising TypeError
        dicts = [{"id": 1, "val": "a"}, {"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
        result = uniq_by(dicts)
        assert len(result) == 2
        assert result[0] == {"id": 1, "val": "a"}
        assert result[1] == {"id": 2, "val": "b"}

    def test_uniq_by_empty(self):
        assert uniq_by([]) == []


# ==========================================
# 7. windowed tests
# ==========================================
class TestWindowed:
    def test_windowed_normal(self):
        items = [1, 2, 3, 4, 5]
        result = list(windowed(items, size=3, step=1))
        assert result == [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    def test_windowed_step_greater_than_one(self):
        items = [1, 2, 3, 4, 5]
        result = list(windowed(items, size=2, step=2))
        assert result == [(1, 2), (3, 4)]

    def test_windowed_with_fill_value(self):
        items = [1, 2, 3, 4, 5]
        result = list(windowed(items, size=3, step=2, fill_value=None))
        # Window 1: [1, 2, 3]
        # Window 2 (idx 2): [3, 4, 5]
        # Window 3 (idx 4): [5, None, None]
        assert result == [(1, 2, 3), (3, 4, 5), (5, None, None)]

    def test_windowed_size_larger_than_iterable_no_fill(self):
        assert list(windowed([1, 2], size=3)) == []

    def test_windowed_size_larger_than_iterable_with_fill(self):
        assert list(windowed([1, 2], size=3, fill_value=0)) == [(1, 2, 0)]

    def test_windowed_empty(self):
        assert list(windowed([], size=3)) == []

    def test_windowed_invalid_args(self):
        with pytest.raises(ValueError, match="size must be >= 1"):
            list(windowed([1, 2], size=0))
        with pytest.raises(ValueError, match="step must be >= 1"):
            list(windowed([1, 2], size=2, step=0))
        with pytest.raises(TypeError):
            list(windowed(12345, size=2))  # type: ignore


# ==========================================
# 8. deep_get tests
# ==========================================
class TestDeepGet:
    def test_deep_get_string_path(self):
        data = {"user": {"profile": {"name": "Alice", "score": 100}}}
        assert deep_get(data, "user.profile.name") == "Alice"
        assert deep_get(data, "user.profile.score") == 100

    def test_deep_get_numeric_key_in_dict(self):
        data = {0: "zero", 1: "one"}
        assert deep_get(data, "0") == "zero"

    def test_deep_get_list_path_with_index(self):
        data = {"items": [{"id": 10}, {"id": 20}]}
        assert deep_get(data, ["items", 1, "id"]) == 20
        assert deep_get(data, "items.0.id") == 10

    def test_deep_get_list_index_out_of_bounds(self):
        data = [10, 20]
        assert deep_get(data, [5], default="out") == "out"
        assert deep_get(data, ["not_an_index"], default="invalid") == "invalid"

    def test_deep_get_custom_separator(self):
        data = {"a/b/c": {"d": 42}, "x": {"y": {"z": 99}}}
        assert deep_get(data, "x/y/z", separator="/") == 99

    def test_deep_get_missing_key_default(self):
        data = {"a": {"b": 1}}
        assert deep_get(data, "a.c.d", default="missing") == "missing"
        assert deep_get(data, "x.y.z", default=None) is None

    def test_deep_get_non_dict_intermediate(self):
        data = {"a": 42}
        assert deep_get(data, "a.b.c", default="fallback") == "fallback"

    def test_deep_get_empty_path(self):
        data = {"a": 1}
        assert deep_get(data, "") == data
        assert deep_get(data, []) == data


# ==========================================
# 9. deep_set tests
# ==========================================
class TestDeepSet:
    def test_deep_set_normal_cow(self):
        orig = {"user": {"profile": {"name": "Alice"}}, "other": 123}
        updated = deep_set(orig, "user.profile.name", "Bob")

        # Original is untouched (Copy-on-Write)
        assert orig["user"]["profile"]["name"] == "Alice"
        assert updated["user"]["profile"]["name"] == "Bob"
        assert updated["other"] == 123

    def test_deep_set_create_intermediate(self):
        orig = {}
        result = deep_set(orig, "config.server.host", "localhost")
        assert result == {"config": {"server": {"host": "localhost"}}}
        assert orig == {}

    def test_deep_set_list_path(self):
        orig = {"a": {"b": 1}}
        result = deep_set(orig, ["a", "c"], 2)
        assert result == {"a": {"b": 1, "c": 2}}

    def test_deep_set_empty_path_error(self):
        with pytest.raises(ValueError, match="path must not be empty"):
            deep_set({"a": 1}, "", 2)
        with pytest.raises(ValueError, match="path must not be empty"):
            deep_set({"a": 1}, [], 2)


# ==========================================
# 10. deep_merge tests
# ==========================================
class TestDeepMerge:
    def test_deep_merge_simple(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        merged = deep_merge(d1, d2)
        assert merged == {"a": 1, "b": 3, "c": 4}
        # Inputs not mutated
        assert d1 == {"a": 1, "b": 2}
        assert d2 == {"b": 3, "c": 4}

    def test_deep_merge_nested(self):
        d1 = {"meta": {"version": 1, "tags": ["a"]}}
        d2 = {"meta": {"author": "wonyoung", "version": 2}}
        merged = deep_merge(d1, d2, deep=True)
        assert merged == {"meta": {"version": 2, "tags": ["a"], "author": "wonyoung"}}

    def test_deep_merge_shallow(self):
        d1 = {"meta": {"version": 1, "tags": ["a"]}}
        d2 = {"meta": {"author": "wonyoung"}}
        merged = deep_merge(d1, d2, deep=False)
        assert merged == {"meta": {"author": "wonyoung"}}

    def test_deep_merge_empty_and_single(self):
        assert deep_merge() == {}
        d = {"a": 1}
        assert deep_merge(d) == {"a": 1}
        assert deep_merge(d) is not d

    def test_deep_merge_invalid_type(self):
        with pytest.raises(TypeError, match="All arguments must be Mapping instances"):
            deep_merge({"a": 1}, [1, 2])  # type: ignore

    def test_deep_merge_circular_reference(self):
        d1: dict = {"a": 1}
        d2: dict = {"b": 2}
        d1["self"] = d1
        with pytest.raises(ValueError, match="Circular reference detected"):
            deep_merge(d1, d2)


# ==========================================
# 11. pick and omit tests
# ==========================================
class TestPickOmit:
    def test_pick_normal(self):
        data = {"id": 1, "name": "Alice", "role": "admin", "secret": "xyz"}
        assert pick(data, "id", "name") == {"id": 1, "name": "Alice"}
        assert pick(data, "id", "nonexistent") == {"id": 1}

    def test_omit_normal(self):
        data = {"id": 1, "name": "Alice", "role": "admin", "secret": "xyz"}
        assert omit(data, "role", "secret") == {"id": 1, "name": "Alice"}
        assert omit(data, "nonexistent") == data

    def test_pick_empty(self):
        assert pick({}) == {}
        assert pick({"a": 1}) == {}

    def test_omit_empty(self):
        assert omit({}) == {}
        assert omit({"a": 1}) == {"a": 1}


# ==========================================
# 12. invert tests
# ==========================================
class TestInvert:
    def test_invert_single(self):
        data = {"a": 1, "b": 2, "c": 3}
        assert invert(data) == {1: "a", 2: "b", 3: "c"}

    def test_invert_single_duplicate_overwrites(self):
        data = {"a": 1, "b": 1, "c": 2}
        # Invert single: 'b' overwrites 'a' for value 1
        assert invert(data) == {1: "b", 2: "c"}

    def test_invert_multi(self):
        data = {"a": 1, "b": 1, "c": 2}
        assert invert(data, multi=True) == {1: ["a", "b"], 2: ["c"]}

    def test_invert_empty(self):
        assert invert({}) == {}
        assert invert({}, multi=True) == {}
