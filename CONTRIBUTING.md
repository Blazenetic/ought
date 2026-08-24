# Contributing to Ought

Thank you for helping make Ought dependable. The project optimises for a small,
coherent public surface rather than feature count.

## Before proposing an API

Read the [library proposal](docs/library-proposal.md) and
[foundation decisions](docs/design-decisions.md). Larger additions should begin
with the practical problem, expected semantics, failure behaviour, and the
reason existing standard-library tools are insufficient.

Ought explicitly does not aim to become a general utilities package, framework,
schema system, alternate async runtime, or database-like collection.

## Set up with uv

```console
git clone https://github.com/Blazenetic/ought.git
cd ought
uv sync --group dev
```

The committed `uv.lock` makes the contributor environment reproducible.

## Set up with pip

```console
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Required checks

Run these before opening a pull request:

```console
pytest
ruff check .
ruff format --check .
mypy
mkdocs build --strict
python -m build
twine check dist/*
```

`pytest` collects docstrings in `src/ought` as doctests and enforces the coverage
threshold configured in `pyproject.toml`.

## Code and documentation style

- Target Python 3.11+ and prefer standard-library vocabulary and behaviour.
- Keep runtime dependencies at zero unless a compelling design decision changes
  that constraint.
- Type every public API and document its errors, mutation, ordering, complexity,
  and context propagation where relevant.
- Add focused tests for the successful path, boundary cases, and failures.
- Include an example that can become a doctest when it stays readable.
- Record decisions that constrain later work in `docs/design-decisions.md`.

Use small, descriptive commits. Pull requests should explain why the change
belongs in Ought, not only what the patch does.
