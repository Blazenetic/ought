from __future__ import annotations

import asyncio
import contextvars

import pytest

from ought import Nursery, nursery


def test_nursery_starts_typed_callables_and_collects_results() -> None:
    async def multiply(value: int, *, factor: int) -> int:
        await asyncio.sleep(0)
        return value * factor

    async def scenario() -> tuple[int, int]:
        async with nursery() as tasks:
            assert isinstance(tasks, Nursery)
            first = tasks.start_soon(multiply, 2, factor=3)
            second = tasks.start_soon(multiply, 4, factor=5)
        return first.result(), second.result()

    assert asyncio.run(scenario()) == (6, 20)


def test_failure_cancels_siblings_and_raises_an_exception_group() -> None:
    cancelled = False

    async def wait_forever() -> None:
        nonlocal cancelled
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled = True
            raise

    async def fail() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("child failed")

    async def scenario() -> None:
        async with nursery() as tasks:
            tasks.start_soon(wait_forever)
            tasks.start_soon(fail)

    with pytest.raises(ExceptionGroup) as error:
        asyncio.run(scenario())

    assert cancelled is True
    assert len(error.value.exceptions) == 1
    assert isinstance(error.value.exceptions[0], RuntimeError)
    assert str(error.value.exceptions[0]) == "child failed"


def test_child_tasks_copy_the_context_present_when_started() -> None:
    request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id")

    async def read_context() -> str:
        await asyncio.sleep(0)
        return request_id.get()

    async def scenario() -> tuple[str, str]:
        token = request_id.set("first")
        try:
            async with nursery() as tasks:
                first = tasks.start_soon(read_context)
                request_id.set("second")
                second = tasks.start_soon(read_context)
            return first.result(), second.result()
        finally:
            request_id.reset(token)

    assert asyncio.run(scenario()) == ("first", "second")


def test_children_can_start_descendants_while_the_group_is_draining() -> None:
    async def scenario() -> str:
        async with nursery() as tasks:

            async def parent() -> str:
                await asyncio.sleep(0)
                child = tasks.start_soon(asyncio.sleep, 0, result="descendant")
                return await child

            parent_task = tasks.start_soon(parent)
        return parent_task.result()

    assert asyncio.run(scenario()) == "descendant"


def test_nursery_rejects_task_starts_after_exit_without_calling_function() -> None:
    called = False

    async def operation() -> None:
        nonlocal called
        called = True

    async def scenario() -> Nursery:
        async with nursery() as tasks:
            pass
        return tasks

    closed = asyncio.run(scenario())
    with pytest.raises(RuntimeError, match="outside an active nursery"):
        closed.start_soon(operation)
    assert called is False


def test_manually_constructed_nursery_is_not_active() -> None:
    called = False

    async def operation() -> None:
        nonlocal called
        called = True

    tasks = Nursery(asyncio.TaskGroup())
    with pytest.raises(RuntimeError, match="outside an active nursery"):
        tasks.start_soon(operation)
    assert called is False
