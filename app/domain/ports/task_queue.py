"""Task queue port protocol for background job processing"""

from typing import Protocol


class TaskQueuePort(Protocol):
    """Protocol for background task queue operations"""

    async def enqueue(
        self,
        task_name: str,
        *,
        job_id: str | None = None,
    ) -> str:
        """Enqueue a background task by name, returning the effective job ID.

        Implementations must silently skip the enqueue when the job is already
        pending or running (deduplication by ``job_id``).
        The ``job_id`` is also passed to the task as its first positional argument.
        """
        ...

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already pending or running."""
        ...

    async def release_job(self, job_id: str) -> None:
        """Delete the dedup key for ``job_id``, allowing it to be re-enqueued.

        Called by the worker after a refresh task finishes (success or failure)
        so that the next SWR cycle can enqueue the same job again immediately.
        The TTL on the key acts as a fallback for crashed workers.
        """
        ...
