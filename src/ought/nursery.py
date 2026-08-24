"""A small ergonomic layer over :class:`asyncio.TaskGroup`.

The public :func:`nursery` context manager intentionally preserves asyncio's
error and cancellation semantics.  It adds only a typed ``start_soon`` method
that accepts an async callable instead of an already-created coroutine.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any, ParamSpec, TypeVar

_P = ParamSpec("_P")
_T = TypeVar("_T")


class Nursery:
    """A live task-starting scope produced by :func:`nursery`.

    ``Nursery`` delegates lifetime, cancellation, and exception grouping to
    :class:`asyncio.TaskGroup`. Context variables are copied by asyncio when
    each task is created, matching :func:`asyncio.create_task`.

    Instances should be obtained from :func:`nursery`, not constructed by
    application code.
    """

    __slots__ = ("_active", "_task_group")

    def __init__(self, task_group: asyncio.TaskGroup) -> None:
        self._task_group = task_group
        self._active = False

    def start_soon(
        self,
        function: Callable[_P, Coroutine[Any, Any, _T]],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> asyncio.Task[_T]:
        """Start an async callable in this nursery and return its task.

        Args:
            function: Async callable to invoke.
            *args: Positional arguments forwarded to ``function``.
            **kwargs: Keyword arguments forwarded to ``function``.

        Raises:
            RuntimeError: If the nursery's context has already exited.
        """
        if not self._active:
            raise RuntimeError("cannot start a task outside an active nursery")
        return self._task_group.create_task(function(*args, **kwargs))

    def _close(self) -> None:
        self._active = False

    def _open(self) -> None:
        self._active = True


@asynccontextmanager
async def nursery() -> AsyncIterator[Nursery]:
    """Open a structured task scope backed by :class:`asyncio.TaskGroup`.

    The context waits for every child task. If one fails, asyncio cancels the
    remaining tasks and raises an exception group after they finish cleaning
    up.

    Example:
        >>> import asyncio
        >>> async def answer(value: int) -> int:
        ...     await asyncio.sleep(0)
        ...     return value
        >>> async def main() -> list[int]:
        ...     async with nursery() as tasks:
        ...         first = tasks.start_soon(answer, 1)
        ...         second = tasks.start_soon(answer, value=2)
        ...     return [first.result(), second.result()]
        >>> asyncio.run(main())
        [1, 2]
    """
    async with asyncio.TaskGroup() as task_group:
        scope = Nursery(task_group)
        scope._open()
        try:
            yield scope
        finally:
            scope._close()


__all__ = ["Nursery", "nursery"]
