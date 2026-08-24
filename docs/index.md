# Ought

Ought is a pure-Python library of focused practical batteries for Python 3.11+.
It has no runtime dependencies and is designed to feel unsurprising beside the
standard library.

The distribution name is `oughtlib`; the import package is `ought`.

## Foundation status

The current `0.1.0a1` foundation is deliberately Settings-centred:

- [`ought.settings`](settings.md) is a usable hierarchical configuration system
  with ordered sources, TOML files, environment values, secrets, clear errors,
  and context-local overrides.
- [`ought.nursery`](nursery.md) is a thin typed layer over
  `asyncio.TaskGroup`. Timeouts, retries, and result helpers remain future design
  work.
- [`ought.multimap`](multimap.md) is a small mutable ordered multi-map without
  secondary indexes.

The public API may move during the alpha period. Its constraints should not:
pure Python, near-zero dependency weight, explicit behaviour, strong typing,
excellent examples, and a surface that fits in one sitting.

## Start here

New users should begin with the [Settings guide](settings.md). Contributors and
subsequent implementation sessions should also read the
[design decisions](design-decisions.md) and [foundation handover](handover.md).

The original [library proposal](library-proposal.md) remains authoritative for
goals, non-goals, and the intended relationship between the three pillars.
