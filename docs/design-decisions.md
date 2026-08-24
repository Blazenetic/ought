# Foundation design decisions

These decisions resolve the implementation questions left open by the library
proposal. They describe the `0.1.0a1` foundation and should be changed
deliberately rather than by accident in a feature patch.

## Distribution and import names

- **Decision:** publish the distribution as `oughtlib`; retain `ought` as the
  Python import package and Ought as the project name.
- **Reason:** on 24 August 2026, `pip index versions ought` reported existing
  `0.2.x` releases, while `oughtlib` returned no matching distribution.
- **Caveat:** an available PyPI name is not reserved until the owner publishes or
  reserves it through PyPI. Recheck immediately before the first release.

## Version and compatibility signal

- **Decision:** begin at `0.1.0a1`, with Python 3.11 as the minimum.
- **Reason:** the code is usable, but the project should communicate that public
  names may move while all three pillars are exercised together.
- **Compatibility:** normal Semantic Versioning begins once the API stabilises;
  alpha releases may make documented breaking changes with a changelog entry.

## Settings precedence and formats

- **Decision:** `defaults < files in order < environment < runtime overrides`.
- **Decision:** TOML is the only file format in the foundation, using Python
  3.11's `tomllib`.
- **Decision:** all mappings merge recursively; later non-mappings replace
  earlier values.
- **Reason:** this is explicit, dependency-free, and covers the common case
  without designing a source plugin framework prematurely.

## Environment convention

- **Decision:** an exact prefix selects names, `__` separates nesting, and path
  segments are lower-cased.
- **Decision:** parse a complete single TOML value when valid; otherwise retain
  the original string. This includes arrays and inline tables, not only scalars.
- **Decision:** conflicting or duplicate normalised paths are errors.
- **Reason:** the convention is familiar, deterministic, and avoids a bespoke
  coercion table.

## Read-only settings snapshots

- **Decision:** Settings is structurally read-only. Mappings and common built-in
  containers are recursively frozen at ingestion; reference cycles in those
  containers are rejected with a source error.
- **Decision:** arbitrary leaf objects are retained by reference. The library
  does not guess how to copy or freeze user-defined values.
- **Decision:** attribute access is dynamic convenience; mapping access and
  typed `require()` are the predictable integration surfaces.
- **Reason:** settings structure should be safe to share across call stacks and
  tasks without pretending that Python can make every opaque object deeply
  immutable. Full schema typing would violate the lightweight core.

## Sensitive values

- **Decision:** `Secret` is an explicit leaf-value wrapper with redacted
  `repr()` and `str()`, plus an explicit `reveal()` operation. A later leaf at
  the same merge location inherits that marker while its sections remain
  mergeable.
- **Decision:** dotted `sensitive=` paths are persistent policies reapplied after
  merging, including for optional and context-overridden values. Intermediate
  components must remain sections.
- **Decision:** dotted paths have no escaping grammar. Literal keys containing a
  dot use mapping access and must be marked with `Secret` directly.
- **Reason:** logging safety should survive environment and runtime overrides.
  The wrapper is intentionally not a secret store or encryption feature.

## Context integration

- **Decision:** only temporary Settings overlays use an Ought-owned
  `ContextVar`. Nursery relies on standard asyncio context copying.
- **Reason:** this gives meaningful task-local behaviour without a global
  "current settings" singleton or a second concurrency model.

## Nursery scope

- **Decision:** the first Nursery is a direct typed wrapper around
  `asyncio.TaskGroup`; it preserves normal waiting, cancellation, and
  `ExceptionGroup` semantics.
- **Decision:** the nursery remains active while `TaskGroup` drains on normal
  exit, allowing child tasks to start descendants. Callable keyword arguments
  remain unambiguous; task metadata uses the returned `asyncio.Task`.
- **Decision:** defer timeout, retry, and bulk-result helpers until their complete
  semantics are designed and tested.
- **Reason:** the standard library already supplies the hard structured
  concurrency guarantees. Ought should add ergonomics, not conceal them.

## MultiMap semantics

- **Decision:** preserve global pair insertion order.
- **Decision:** the ordinary mutable mapping view exposes the first value;
  assignment and deletion affect all values for that key.
- **Decision:** `getall()` returns an immutable tuple and `pairs()` returns a
  stable snapshot iterator.
- **Decision:** key matching follows dictionary identity-or-equality semantics;
  mutation validates and prepares both internal indexes before committing.
- **Decision:** secondary indexes are excluded from the core type.
- **Reason:** the split is explicit and useful while staying understandable.
  Index maintenance would push the collection towards the proposal's database
  non-goal.

## Still open

- Which individual Nursery helpers earn inclusion after real usage.
- Whether MultiMap needs a precisely defined single-pair removal operation.
- Project ownership and release automation for the first PyPI publication.
- The point at which alpha compatibility gives way to a stable public contract.
