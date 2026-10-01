import asyncio
from collections.abc import Coroutine
from typing import Any

# asyncio only keeps weak references to running tasks, so a fire-and-forget
# create_task() can be garbage-collected mid-run unless something holds it.
_running: set[asyncio.Task] = set()


def spawn(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _running.add(task)
    task.add_done_callback(_running.discard)
    return task
