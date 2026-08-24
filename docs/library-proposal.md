# Ought — A focused pure-Python library of the missing practical batteries

**One-sentence summary**  
Ought is a small, pure-Python library that provides three tightly-scoped, high-quality utilities that most real programs need and that currently force developers to assemble from multiple overlapping packages: hierarchical configuration, lightweight structured concurrency helpers, and efficient ordered multi-maps.

**Status**

Accepted design proposal — initial `0.1.0a1` foundation implemented.
Date: 2026-08-17
Author: Blazenetic (with Grok)

**Implementation note (2026-08-24)**

The distribution name is `oughtlib`; the import package and project remain
`ought` / Ought. Foundation decisions that resolve this proposal's open
questions are recorded in [design-decisions.md](design-decisions.md).

---

## Motivation

Python’s ecosystem is rich, yet three recurring problems still produce more friction than they should:

1. **Configuration** — Loading, merging, validating and overriding settings from defaults, files, environment variables and runtime values remains fragmented. Developers repeatedly choose between heavy frameworks or fragile ad-hoc code.
2. **Structured concurrency** — `asyncio.TaskGroup` (3.11+) is a major improvement, but everyday scripts and services still lack a thin, ergonomic layer for nurseries, context-aware timeouts/retries, and clean result collection that carries `contextvars`.
3. **Ordered multi-value collections** — Looking things up by key while preserving order and supporting multiple values (or secondary indexes) forces either `dict` of lists, multiple parallel structures, or heavier third-party collections.

Existing libraries solve pieces well (boltons, more-itertools, sortedcontainers, pydantic-settings, anyio, tenacity, etc.). None owns the *intersection* with a single coherent, lightweight, pure-Python design that feels like it belongs next to the standard library.

Ought exists to fill that gap cleanly.

---

## Goals

- Provide a small, high-quality surface that feels inevitable rather than competitive.
- Stay pure-Python with zero (or near-zero) hard dependencies.
- Make the common 80 % of config + concurrency + multi-key lookup work safer, clearer and less repetitive.
- Be documentation-first, strongly typed, and friendly to structural pattern matching and modern Python (3.11+).
- Remain small enough that it can be vendored without guilt or pinned without fear of bloat.

## Non-goals (actively refused)

- Another general-purpose utility kitchen sink.
- A full application framework, DI container, web server, CLI framework, or workflow engine.
- Replacing anyio, Trio, or pydantic.
- Heavy validation / schema systems (optional integration is fine; core stays light).
- Sync/async dual APIs that double the surface area.
- Secondary indexes that turn the collection into a full database.
- Anything that would require native code or significant external dependencies to be useful.

---

## Design principles

1. Pure Python first.
2. “What would the standard library do?” as the default design question.
3. Small surface area — refuse scope creep.
4. Explicit about mutability, performance characteristics, and context propagation.
5. Strong typing + excellent doctests that show real usage.
6. Contextvars-aware by default where it matters.
7. Easy to understand in one sitting; easy to vendor.

---

## The three pillars

### 1. Hierarchical configuration (`ought.settings`)

A single, composable `Settings` object that:

- Merges sources with explicit, documented precedence (defaults → file(s) → env → runtime overrides).
- Supports nested structures cleanly.
- Offers both attribute and mapping access.
- Marks sensitive values so they are not accidentally logged or printed.
- Produces clear, actionable errors on missing or invalid values.
- Is contextvars-aware so call stacks can temporarily override layers.

Minimal usage sketch:

```python
from ought import Settings

settings = Settings.from_sources(
    defaults={"timeout": 30, "db": {"host": "localhost"}},
    files=["config.toml"],
    env_prefix="MYAPP_",
)

print(settings.timeout)
print(settings.db.host)

with settings.override(timeout=5):
    ...
```

### 2. Lightweight structured concurrency helpers (`ought.nursery`)

Thin, practical layer on top of `asyncio` (compatible with anyio where useful):

- Nursery / task-group style grouping with automatic cancellation propagation.
- Context-aware timeouts and simple retry helpers that carry contextvars.
- Clean “run these callables concurrently and collect results/errors” utilities.

Goal: make the common concurrent patterns in scripts and small services safer and more readable without forcing a different concurrency model.

```python
from ought import nursery

async with nursery() as n:
    n.start_soon(fetch_a)
    n.start_soon(fetch_b)
    # normal exit waits; a child failure cancels its siblings
```

### 3. Ordered multi-maps (`ought.multimap`)

Collections that:

- Preserve insertion order.
- Support multiple values per key cleanly.
- Feel like a natural extension of `dict` / `OrderedDict`.
- Keep secondary-index support optional and thin (not a core requirement of the basic type).

```python
from ought import MultiMap

mm = MultiMap()
mm.add("user", 42)
mm.add("user", 99)
list(mm.getall("user"))  # [42, 99]
```

---

## Naming

**Recommended name: Ought**

- Short, distinctive, and memorable.
- Directly signals the intent: “these are the pieces that *ought* to exist in (or next to) the standard library.”
- Avoids the “yet another utils/helpers/kit” problem.
- Easy to type and to say.
- Distribution name: `oughtlib` (`ought` was already occupied on PyPI when the
  foundation was implemented).
- Import package: `ought`, preserving the proposed API and project identity.

Alternative candidates considered and rejected for now:
- `solid` — good but less specific.
- `stdlibx` / `batteries` — too generic or already culturally loaded.
- `missing` — accurate in conversation but negative as a long-term brand.
- `bolt` / `boltonx` — too close to the excellent existing boltons project.

---

## Relationship to existing libraries

- **Complementary** to boltons and more-itertools (steal good ideas, do not duplicate their general utility role).
- **Lighter and more opinionated** than the major configuration libraries.
- **Does not try to replace** anyio, Trio, or pydantic — it sits above or beside them for the common cases.
- Success looks like “I reach for Ought the same way I reach for pathlib or dataclasses.”

---

## Success criteria

- A developer can understand the entire public surface in under 30 minutes.
- The three pillars feel cohesive rather than three unrelated tools in one package.
- It is easy and safe to add as a dependency (or vendor) in both scripts and production services.
- Documentation is good enough that people rarely need to read the source for normal use.
- Scope remains stable; new features are rare and hard-won.

---

## Suggested next steps

1. Confirm name availability on PyPI (`ought` / `oughtlib`). **Completed for the
   foundation: `oughtlib` selected; recheck before publication.**
2. Create a minimal repository with: **Completed.**
   - Clear README that states goals and non-goals up front.
   - Package layout for the three pillars.
   - Initial `Settings` implementation (highest everyday value).
   - Basic test suite and documentation skeleton.
3. Implement the concurrency helpers next (they benefit most from modern asyncio).
   **A thin TaskGroup nursery now exists; timeout, retry and collection helpers
   remain the recommended next slice.**
4. Add `MultiMap` once the first two pillars feel solid. **A thin ordered
   MultiMap now exists without secondary indexes.**
5. Publish a 0.1 with explicit “API may still move” marking.
6. Keep the project ruthlessly small.

---

## Open questions

- Exact precedence rules and file format support for Settings. **Resolved for
  the foundation: defaults → TOML files → environment → overrides.**
- How aggressive to be with contextvars integration in the concurrency helpers.
  **Resolved conservatively: preserve asyncio's native task context copying.**
- Whether `MultiMap` should support secondary indexes in the core type or as a
  separate thin wrapper. **Resolved: no secondary indexes in the core.**
- Long-term home (standalone open-source project under Blazenetic / Complex State, or personal).
- Versioning and compatibility policy once 0.1 ships.

---

*This proposal is intentionally concise. The goal is a library that stays small, clear, and useful for years rather than a large surface that needs constant expansion.*
