"""An insertion-ordered mapping from keys to one or more values.

``MultiMap`` presents the first value for each key through the ordinary mapping
protocol and exposes every value explicitly through :meth:`MultiMap.getall` and
:meth:`MultiMap.pairs`.

>>> users = MultiMap([("user", 42), ("role", "editor")])
>>> users.add("user", 99)
>>> users["user"]
42
>>> users.getall("user")
(42, 99)
>>> list(users.pairs())
[('user', 42), ('role', 'editor'), ('user', 99)]
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from typing import Generic, TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")


class MultiMap(MutableMapping[_K, _V], Generic[_K, _V]):
    """A mutable mapping that retains all values and global insertion order.

    The standard mapping view contains one entry per distinct key and exposes
    its first value. Assigning with ``multi_map[key] = value`` replaces every
    value for that key; :meth:`add` appends another value instead.

    ``add`` and first-value lookup are O(1) on average. ``getall`` is O(m) to
    copy the *m* values for a key. Assignment and deletion of an existing key
    are O(n) because they preserve global pair order. The type deliberately has
    no secondary-index machinery.
    """

    __slots__ = ("_pairs", "_values")

    def __init__(self, pairs: Iterable[tuple[_K, _V]] = ()) -> None:
        self._pairs: list[tuple[_K, _V]] = []
        self._values: dict[_K, list[_V]] = {}
        for key, value in pairs:
            self.add(key, value)

    def add(self, key: _K, value: _V) -> None:
        """Append ``value`` for ``key`` without replacing existing values."""
        values = self._values.get(key)
        if values is None:
            self._values[key] = [value]
        else:
            values.append(value)
        self._pairs.append((key, value))

    def getall(self, key: _K) -> tuple[_V, ...]:
        """Return all values for ``key`` in insertion order.

        Raises:
            KeyError: If ``key`` is absent.
        """
        return tuple(self._values[key])

    def pairs(self) -> Iterator[tuple[_K, _V]]:
        """Iterate over a stable snapshot of all key-value pairs in order."""
        return iter(tuple(self._pairs))

    def copy(self) -> MultiMap[_K, _V]:
        """Return a shallow copy retaining every pair."""
        return MultiMap(self._pairs)

    def __getitem__(self, key: _K) -> _V:
        return self._values[key][0]

    def __setitem__(self, key: _K, value: _V) -> None:
        if key not in self._values:
            self.add(key, value)
            return

        try:
            first_position = next(
                index
                for index, (existing_key, _) in enumerate(self._pairs)
                if _keys_match(existing_key, key)
            )
        except StopIteration:
            raise RuntimeError("MultiMap key index is inconsistent") from None

        canonical_key = self._pairs[first_position][0]
        pairs = [pair for pair in self._pairs if not _keys_match(pair[0], key)]
        pairs.insert(first_position, (canonical_key, value))
        self._values[key] = [value]
        self._pairs = pairs

    def __delitem__(self, key: _K) -> None:
        # Validate lookup and build the replacement before mutating either index.
        self._values[key]
        pairs = [pair for pair in self._pairs if not _keys_match(pair[0], key)]
        del self._values[key]
        self._pairs = pairs

    def __iter__(self) -> Iterator[_K]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._pairs!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MultiMap):
            return NotImplemented
        return self._pairs == other._pairs


def _keys_match(existing: object, candidate: object) -> bool:
    """Use the identity-or-equality rule employed by Python dictionaries."""
    return existing is candidate or existing == candidate


__all__ = ["MultiMap"]
