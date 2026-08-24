# MultiMap

`MultiMap` is a mutable mapping from each key to one or more values. It preserves
the global insertion order of every key-value pair while providing a normal
mapping view over the first value for each distinct key.

## Core operations

```python
from ought import MultiMap

values = MultiMap([("a", 1), ("b", 2)])
values.add("a", 3)

values["a"]  # 1
values.getall("a")  # (1, 3)
list(values)  # ["a", "b"]
list(values.pairs())  # [("a", 1), ("b", 2), ("a", 3)]
```

The distinction between mapping operations and multi-value operations is
explicit:

| Operation | Meaning |
| --- | --- |
| `values[key]` | Return the first value; raise `KeyError` if absent |
| `values[key] = item` | Replace every value for the key with one value |
| `values.add(key, item)` | Append another pair without replacing |
| `values.getall(key)` | Return all values as a tuple; raise `KeyError` if absent |
| `values.pairs()` | Iterate over a stable snapshot of every pair |
| `del values[key]` | Remove every value for the key |
| `len(values)` | Count distinct keys, not pairs |

Because `MultiMap` implements `MutableMapping`, familiar methods such as
`get()`, `items()`, `update()`, and `pop()` operate on the first-value mapping
view. Use `pairs()` whenever multiplicity matters.

Keys follow normal `dict` rules: they must be hashable, and matching uses
identity or equality. Assignment through an equal key retains the original
first stored key object. A rejected unhashable key leaves both the mapping view
and global pair order unchanged.

## Ordering

`pairs()` preserves global pair insertion order, including interleaved keys.
Replacing an existing key puts its single replacement at the position of that
key's first pair. Deleting and later re-adding a key moves it to the end of the
distinct-key mapping order.

The iterator returned by `pairs()` is a snapshot. Mutating the MultiMap after
requesting the iterator does not change what that iterator yields.

## Complexity

| Operation | Complexity |
| --- | --- |
| `add()` | O(1) amortised |
| first-value lookup | O(1) average |
| `getall()` | O(m) to create the returned tuple of *m* values |
| assignment of an existing key | O(n) pairs |
| deletion | O(n) pairs |
| `pairs()` | O(n) to create a stable snapshot |

The implementation keeps a global pair list plus a per-key value index. This is
intentional duplication for a small type that needs both exact ordering and fast
lookup.

## Deliberate limits

There are no secondary indexes, database-style queries, sorting modes, or
thread-safety guarantees. Adding a single-pair removal operation remains a
possible future refinement, but its equality and ordering semantics should be
decided before expanding the API.
