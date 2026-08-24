# Nursery

`ought.nursery` is a typed convenience layer over `asyncio.TaskGroup`. It does
not introduce another concurrency model or alter asyncio's cancellation and
exception semantics.

## Starting tasks

```python
import asyncio

from ought import nursery


async def fetch(identifier: int, *, delay: float = 0) -> str:
    await asyncio.sleep(delay)
    return f"item-{identifier}"


async def main() -> list[str]:
    async with nursery() as tasks:
        first = tasks.start_soon(fetch, 1)
        second = tasks.start_soon(fetch, 2, delay=0.01)

    return [first.result(), second.result()]
```

`start_soon()` accepts an async callable plus typed positional and keyword
arguments. It returns the ordinary `asyncio.Task`, so results and task metadata
use familiar asyncio APIs.

## Lifetime and failures

The behaviour is exactly the underlying `TaskGroup` behaviour:

- normal context exit waits for all child tasks;
- the first non-cancellation child failure cancels its siblings;
- cleanup is awaited; and
- failures are raised as an `ExceptionGroup`.

The scope rejects `start_soon()` after it exits and checks this before invoking
the async callable, avoiding an un-awaited coroutine as a side effect.

## Context variables

`asyncio.TaskGroup.create_task()` copies the current context when each task is
created. Ought preserves that behaviour. Two tasks started under different
`ContextVar` values each retain the value active at their own creation time.

This composes directly with `Settings.override()`:

```python
async def run_with_override() -> None:
    with settings.override(timeout=5):
        async with nursery() as tasks:
            tasks.start_soon(operation_using_settings)
```

## Deliberate limits

The foundation does not yet add timeouts, retries, or bulk result collection.
Those remain proposed parts of the concurrency pillar, but each needs one clear
set of semantics before becoming public API. In particular, retry cancellation,
exception filtering, backoff timing, and result ordering should not be guessed
incrementally.

Use `asyncio.timeout()` directly today. Use a specialised retry library when a
project needs policy beyond a small future Ought helper.
