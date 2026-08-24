from __future__ import annotations

from collections.abc import MutableMapping

import pytest

from ought import MultiMap


def test_add_and_getall_preserve_global_pair_order() -> None:
    values: MultiMap[str, int] = MultiMap()
    values.add("a", 1)
    values.add("b", 2)
    values.add("a", 3)

    assert values["a"] == 1
    assert values.getall("a") == (1, 3)
    assert list(values.pairs()) == [("a", 1), ("b", 2), ("a", 3)]
    assert list(values) == ["a", "b"]
    assert len(values) == 2


def test_standard_mapping_view_exposes_the_first_value() -> None:
    values = MultiMap([("header", "first"), ("header", "second"), ("other", "x")])

    assert isinstance(values, MutableMapping)
    assert dict(values) == {"header": "first", "other": "x"}
    assert list(values.items()) == [("header", "first"), ("other", "x")]


def test_assignment_replaces_all_values_at_the_first_pair_position() -> None:
    values = MultiMap([("a", 1), ("b", 2), ("a", 3), ("c", 4)])

    values["a"] = 9
    values["new"] = 10

    assert values.getall("a") == (9,)
    assert list(values.pairs()) == [
        ("a", 9),
        ("b", 2),
        ("c", 4),
        ("new", 10),
    ]
    assert list(values) == ["a", "b", "c", "new"]


def test_deletion_removes_every_value_and_readding_moves_key_to_end() -> None:
    values = MultiMap([("a", 1), ("b", 2), ("a", 3)])

    del values["a"]
    values.add("a", 4)

    assert list(values) == ["b", "a"]
    assert list(values.pairs()) == [("b", 2), ("a", 4)]


def test_missing_keys_follow_mapping_conventions() -> None:
    values: MultiMap[str, int] = MultiMap()

    with pytest.raises(KeyError):
        _ = values["missing"]
    with pytest.raises(KeyError):
        values.getall("missing")
    with pytest.raises(KeyError):
        del values["missing"]


def test_pairs_iterator_is_a_stable_snapshot() -> None:
    values = MultiMap([("a", 1)])
    snapshot = values.pairs()

    values.add("b", 2)

    assert list(snapshot) == [("a", 1)]
    assert list(values.pairs()) == [("a", 1), ("b", 2)]


def test_copy_equality_and_repr_include_every_pair() -> None:
    values = MultiMap([("a", 1), ("a", 2)])
    copied = values.copy()

    assert copied == values
    assert copied is not values
    assert repr(values) == "MultiMap([('a', 1), ('a', 2)])"
    assert values != {"a": 1}

    copied.add("a", 3)
    assert copied != values
    assert values.getall("a") == (1, 2)
