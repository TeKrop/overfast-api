"""Task queue port protocol for background job processing"""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Coroutine


class TaskQueuePort(Protocol):
    """Protocol for background task queue operations (arq in Phase 5)"""

    async def enqueue(
        self,
        task_name: str,
        *args: Any,
        job_id: str | None = None,
        coro: Coroutine[Any, Any, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Enqueue a background task.

        ``coro``, when provided, is executed immediately (Phase 4 asyncio) or
        dispatched to a worker process (Phase 5 arq).  ``task_name`` is kept for
        arq compatibility and logging.
        Returns the effective job ID.
        """
        ...

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already pending or running."""
        ...
