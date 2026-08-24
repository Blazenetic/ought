# Ought

[![CI](https://github.com/Blazenetic/ought/actions/workflows/ci.yml/badge.svg)](https://github.com/Blazenetic/ought/actions/workflows/ci.yml)

Focused practical batteries for modern Python.

Ought provides three deliberately small utilities that often sit just outside
the standard library:

1. hierarchical application settings;
2. an ergonomic `asyncio.TaskGroup` nursery; and
3. insertion-ordered multi-value mappings.

It is pure Python, has no runtime dependencies, targets Python 3.11+, and is
small enough to understand or vendor without inheriting a framework.

> **Status:** `0.1.0a1` foundation. The Settings API is usable and tested; the
> Nursery and MultiMap APIs are intentionally thin. The public API may still
> move before the first stable release.

The distribution is named **`oughtlib`** because `ought` is already occupied on
PyPI. The import package remains the cleaner **`ought`**:

```python
from ought import MultiMap, Secret, Settings, nursery
```

## What is implemented

| Pillar | Initial surface | Foundation status |
| --- | --- | --- |
| `ought.settings` | layered TOML/environment settings, nested access, secrets, typed requirements, context-local overrides | Primary implementation |
| `ought.nursery` | typed async callable scheduling over `asyncio.TaskGroup` | Thin and usable |
| `ought.multimap` | mutable first-value mapping view plus ordered `getall()` and `pairs()` | Thin and usable |

The [library proposal](docs/library-proposal.md) remains the source of truth for
the project's goals and non-goals. The
[foundation decisions](docs/design-decisions.md) record how its open questions
were resolved for this implementation.

## Installation

`oughtlib` has not yet had its first PyPI release. Until then, install directly
from GitHub:

```console
python -m pip install "oughtlib @ git+https://github.com/Blazenetic/ought.git"
```

Or with uv:

```console
uv add "oughtlib @ git+https://github.com/Blazenetic/ought.git"
```

After the first release, the package name will be:

```console
python -m pip install oughtlib
```

## Settings quick start

Given a TOML file:

```toml
# config.toml
timeout = 30

[db]
host = "localhost"
port = 5432
```

Build a settings snapshot from ordered sources:

```python
from ought import Secret, Settings

settings = Settings.from_sources(
    defaults={
        "debug": False,
        "db": {"password": Secret("development-only")},
    },
    files=["config.toml"],
    env_prefix="MYAPP_",
    overrides={"timeout": 20},
)

settings.timeout  # 20
settings.db.host  # "localhost"
settings["db"]["port"]  # 5432
```

Precedence is always:

```text
defaults < files in order < environment < runtime overrides
```

Environment variables use `__` for nesting and complete TOML value syntax where
possible:

```console
export MYAPP_DEBUG=true
export MYAPP_DB__PORT=6432
export MYAPP_DB__PASSWORD=production-secret
```

Use `require()` when a missing value or wrong type should fail clearly:

```python
port = settings.require("db.port", int)
```

Temporary overrides are task-local and restore automatically:

```python
with settings.override(timeout=5):
    assert settings.timeout == 5

assert settings.timeout == 20
```

Values marked with `Secret` have redacted `str()` and `repr()` output. Accessing
the raw value is deliberately explicit:

```python
password = settings.db.password
password  # Secret(<redacted>)
password.reveal()  # pass deliberately to the database client
```

See the [Settings guide](docs/settings.md) for merging, environment parsing,
immutability, error behaviour, and context propagation details.

## Nursery quick start

```python
import asyncio

from ought import nursery


async def fetch(name: str) -> str:
    await asyncio.sleep(0.01)
    return name.upper()


async def main() -> list[str]:
    async with nursery() as tasks:
        first = tasks.start_soon(fetch, "alpha")
        second = tasks.start_soon(fetch, "beta")
    return [first.result(), second.result()]
```

Normal exit waits for all children. A child failure uses standard
`asyncio.TaskGroup` cancellation and `ExceptionGroup` behaviour. See the
[Nursery guide](docs/nursery.md).

## MultiMap quick start

```python
from ought import MultiMap

headers = MultiMap()
headers.add("accept", "text/html")
headers.add("accept", "application/json")

headers["accept"]  # "text/html" (the first value)
headers.getall("accept")  # ("text/html", "application/json")
list(headers.pairs())  # every pair, in global insertion order
```

Assignment replaces all values for a key; `add()` appends. Secondary indexes
are intentionally out of scope. See the [MultiMap guide](docs/multimap.md).

## Development

With uv:

```console
git clone https://github.com/Blazenetic/ought.git
cd ought
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run mkdocs build --strict
uv build
```

With standard Python tooling:

```console
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy
mkdocs build --strict
python -m build
```

Tests include source doctests and enforce branch-aware coverage. See
[CONTRIBUTING.md](CONTRIBUTING.md) before proposing a larger API: keeping Ought
small is a feature, not an unfinished task.

## Design boundaries

Ought is not a validation framework, dependency injection container, general
utility collection, alternate async runtime, retry framework, or embedded
database. New features should solve a repeated practical problem while keeping
the public surface understandable in one sitting.

## Licence

MIT. See [LICENSE](LICENSE).
