"""AsyncIO task queue adapter — Phase 4 in-process background tasks with deduplication"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, ClassVar

from app.metaclasses import Singleton
from app.monitoring.metrics import (
    background_tasks_duration_seconds,
    background_tasks_queue_size,
    background_tasks_total,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine


class AsyncioTaskQueue(metaclass=Singleton):
    """In-process task queue backed by asyncio.create_task().

    Uses a class-level set for deduplication so concurrent requests don't
    trigger duplicate refreshes for the same entity.

    When a ``coro`` is provided to ``enqueue``, it is executed as a real
    background task.  Phase 5 will replace this adapter with an arq-backed
    one that dispatches to a worker process instead, but the interface stays
    the same.
    """

    _pending_jobs: ClassVar[set[str]] = set()

    async def enqueue(  # NOSONAR
        self,
        task_name: str,
        *_args: Any,
        job_id: str | None = None,
        coro: Coroutine[Any, Any, Any] | None = None,
        on_complete: Callable[[str], Awaitable[None]] | None = None,
        on_failure: Callable[[str, Exception], Awaitable[None]] | None = None,
        **_kwargs: Any,
    ) -> str:
        """Schedule a background task if not already pending."""
        effective_id = job_id or task_name
        if effective_id in self._pending_jobs:
            logger.debug(f"[TaskQueue] Skipping duplicate job: {effective_id}")
            if coro is not None:
                coro.close()  # avoid "coroutine was never awaited" warning
            return effective_id

        self._pending_jobs.add(effective_id)
        background_tasks_queue_size.labels(task_type=task_name).inc()

        async def _run() -> None:
            start = time.monotonic()
            status = "success"
            try:
                logger.info(
                    f"[TaskQueue] Running task '{task_name}' (job_id={effective_id})"
                )
                if coro is not None:
                    await coro
                if on_complete is not None:
                    await on_complete(effective_id)
            except Exception as exc:  # noqa: BLE001
                status = "failure"
                logger.warning(
                    f"[TaskQueue] Task '{task_name}' (job_id={effective_id}) failed: {exc}"
                )
                if on_failure is not None:
                    await on_failure(effective_id, exc)
            finally:
                elapsed = time.monotonic() - start
                background_tasks_total.labels(task_type=task_name, status=status).inc()
                background_tasks_duration_seconds.labels(task_type=task_name).observe(
                    elapsed
                )
                background_tasks_queue_size.labels(task_type=task_name).dec()
                self._pending_jobs.discard(effective_id)

        task = asyncio.create_task(_run(), name=effective_id)
        task.add_done_callback(lambda _: None)
        return effective_id

    async def is_job_pending_or_running(self, job_id: str) -> bool:  # NOSONAR
        """Return True if a job with this ID is already in-flight."""
        return job_id in self._pending_jobs
