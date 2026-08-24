# Foundation merge handover

## Merge status

Draft PR #1 received a focused senior design review on 24 August 2026. The
foundation is ready to become the `0.1.0a1` base: no known implementation or API
design blocker remains. The decisions that follow-on work must preserve are in
[design-decisions.md](design-decisions.md).

The review deliberately did not implement the proposed timeout, retry, or
result-collection helpers.

## Review changes

- Settings now rejects cyclic supported containers with a path-aware
  `SettingsSourceError`, validates environment container/name/prefix shapes,
  and has explicit contracts for TOML values, opaque mutable leaves, dotted
  paths, sensitivity policies, and task inheritance/isolation.
- Nursery now remains live for the full `asyncio.TaskGroup` lifetime, including
  the period in which child tasks drain and may start descendants.
- MultiMap mutation is atomic for rejected unhashable keys and follows
  dictionary identity-or-equality semantics for equal and non-reflexive keys.
- CI now smoke-tests the built wheel after distribution validation.

## Current foundation

Version `0.1.0a1` provides:

- modern Hatchling packaging under the `oughtlib` distribution name;
- a zero-dependency, typed `ought` package for Python 3.11+;
- the primary Settings implementation and its error, secret, source, and
  context-override behaviours;
- thin but functional Nursery and MultiMap pillars;
- doctests, focused unit and async tests, strict typing and linting, coverage,
  MkDocs documentation, build validation, and a Python 3.11–3.14 CI matrix.

## Verification evidence

The post-review tree passed:

- 52 unit, async, and source-doctest cases on Python 3.11.15, 3.12.13, and
  3.14.6;
- 99.23% branch-aware coverage;
- strict Ruff formatting/linting and strict mypy;
- strict MkDocs generation;
- lockfile validation, sdist and wheel builds, and Twine checks; and
- no-dependency wheel installation and import smoke tests in clean Python 3.11
  and 3.14 virtual environments, including the `py.typed` marker.

The repeatable uv commands are:

```console
uv sync --group dev
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run mkdocs build --strict
uv build
uv run twine check dist/*
```

The classic-tooling path is `python -m pip install -e ".[dev]"` followed by the
same tool commands without `uv run`.

## Remaining human decisions

These are release-operation or future-scope decisions, not merge blockers:

- recheck and secure the `oughtlib` PyPI project immediately before publishing;
- choose PyPI ownership and trusted-publishing configuration;
- decide whether hosted API documentation is required for the first alpha; and
- decide later which individual Nursery helper semantics earn inclusion and
  when alpha compatibility becomes stable.

## Recommended next phase

Make the concurrency pillar the next primary slice, but keep it bounded:

1. Write a short behaviour proposal for at most three helpers: timeout scope,
   retry, and ordered concurrent result collection.
2. Decide cancellation, exception filtering, backoff, result ordering, and
   context propagation before naming the APIs.
3. Implement only the helpers whose semantics stay small beside asyncio.
4. Add deterministic async tests, doctests, and guide examples for every public
   behaviour.
5. Exercise Settings and Nursery together in one realistic example without
   creating an application framework.

MultiMap should receive only targeted hardening in that phase. A single-pair
removal operation is the most plausible addition, but it needs an explicit rule
for duplicate equal values before implementation.

## Scope guardrails

Do not add YAML, a source plugin framework, schema generation, sync concurrency,
secondary indexes, or a general collection of helpers merely to make the
package look broader. The foundation is intentionally impressive through
coherence, tests, and documentation rather than API count.
