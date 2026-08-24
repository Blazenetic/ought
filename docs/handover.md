# Foundation handover

This is the starting point for the next bounded implementation session.

## Current foundation

Version `0.1.0a1` provides:

- modern Hatchling packaging under the `oughtlib` distribution name;
- a zero-dependency, typed `ought` package for Python 3.11+;
- the primary Settings implementation and its error, secret, source, and
  context-override behaviours;
- thin but functional Nursery and MultiMap pillars;
- doctests, focused unit and async tests, strict typing and linting, coverage,
  MkDocs documentation, build validation, and a Python 3.11–3.14 CI matrix.

The decisions that must remain stable during follow-on work are recorded in
[design-decisions.md](design-decisions.md).

## Verification baseline

From a uv environment:

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

## Release-readiness backlog

After the concurrency slice:

- recheck and secure the `oughtlib` PyPI project name;
- choose trusted publishing ownership and release workflow;
- test the built wheel in clean Python 3.11 and 3.14 environments;
- decide whether API docs need hosted MkDocs before the first alpha;
- add security and support policies if external contributors arrive; and
- publish release notes that emphasise alpha compatibility.

## Scope guardrails

Do not add YAML, a source plugin framework, schema generation, sync concurrency,
secondary indexes, or a general collection of helpers merely to make the
package look broader. The foundation is intentionally impressive through
coherence, tests, and documentation rather than API count.
