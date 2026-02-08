"""Task queue port protocol for background job processing"""

from typing import Any, Protocol


class TaskQueuePort(Protocol):
    """Protocol for background task queue operations (arq in v4)"""

    async def enqueue(
        self,
        task_name: str,
        *args: Any,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Enqueue a background task, returns job ID"""
        ...

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Check if job is already pending or running (for deduplication)"""
        ...
