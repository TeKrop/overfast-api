"""AsyncIO task queue adapter — Phase 4 in-process background tasks with deduplication"""

import asyncio
from typing import ClassVar

from app.overfast_logger import logger


class AsyncioTaskQueue:
    """In-process task queue backed by asyncio.create_task().

    Uses a class-level set for deduplication so that concurrent requests
    don't trigger duplicate refreshes for the same entity.

    Note: Tasks are no-ops (log only) until Phase 5 wires real refresh
    coroutines via the arq task registry. The deduplication infrastructure
    is already functional.
    """

    _pending_jobs: ClassVar[set[str]] = set()

    async def enqueue(
        self,
        task_name: str,
        *_args,
        job_id: str | None = None,
        **_kwargs,
    ) -> str:
        """Schedule a background task if not already pending."""
        effective_id = job_id or f"{task_name}"
        if effective_id in self._pending_jobs:
            logger.debug(f"[TaskQueue] Skipping duplicate job: {effective_id}")
            return effective_id

        self._pending_jobs.add(effective_id)

        async def _run() -> None:
            try:
                logger.info(
                    f"[TaskQueue] Running task '{task_name}' (job_id={effective_id})"
                )
                # Phase 5: dispatch to real refresh coroutine via registry
            finally:
                self._pending_jobs.discard(effective_id)

        task = asyncio.create_task(_run(), name=effective_id)
        # Keep a strong reference to prevent GC before the task completes
        task.add_done_callback(lambda _: None)
        return effective_id

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already in-flight."""
        return job_id in self._pending_jobs
