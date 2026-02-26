"""AsyncIO task queue adapter — in-process deduplication for tests"""

from typing import Any, ClassVar

from app.metaclasses import Singleton
from app.overfast_logger import logger


class AsyncioTaskQueue(metaclass=Singleton):
    """In-process task queue used in tests as a drop-in for :class:`ValkeyTaskQueue`.

    Provides deduplication via a class-level set; does not execute any work.
    The actual task execution is handled by the taskiq worker in production.
    """

    _pending_jobs: ClassVar[set[str]] = set()

    async def enqueue(
        self,
        task_name: str,
        *_args: Any,
        job_id: str | None = None,
        **_kwargs: Any,
    ) -> str:
        """Record a job as pending, skipping duplicates."""
        effective_id = job_id or task_name
        if effective_id in self._pending_jobs:
            logger.debug("[TaskQueue] Skipping duplicate job: %s", effective_id)
            return effective_id
        self._pending_jobs.add(effective_id)
        logger.debug("[TaskQueue] Enqueued: %s", effective_id)
        return effective_id

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already pending."""
        return job_id in self._pending_jobs
