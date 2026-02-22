"""Task queue port protocol for background job processing"""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine


class TaskQueuePort(Protocol):
    """Protocol for background task queue operations (arq in Phase 5)"""

    async def enqueue(
        self,
        task_name: str,
        *args: Any,
        job_id: str | None = None,
        coro: Coroutine[Any, Any, Any] | None = None,
        on_complete: Callable[[str], Awaitable[None]] | None = None,
        on_failure: Callable[[str, Exception], Awaitable[None]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Enqueue a background task.

        ``coro``, when provided, is executed immediately (Phase 4 asyncio) or
        dispatched to a worker process (Phase 5 arq).  ``task_name`` is kept for
        arq compatibility and logging.

        ``on_complete(job_id)`` is awaited when the task finishes successfully.
        ``on_failure(job_id, exc)`` is awaited when the task raises an exception.
        Both callbacks are optional and intended for domain-level monitoring.

        Returns the effective job ID.
        """
        ...

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already pending or running."""
        ...
