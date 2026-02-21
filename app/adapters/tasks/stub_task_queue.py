"""Stub task queue adapter — Phase 4 placeholder until arq is wired in Phase 5"""

from app.overfast_logger import logger


class StubTaskQueue:
    """No-op implementation of TaskQueuePort.

    Logs enqueue calls for observability but does not actually execute tasks.
    Will be replaced by ArqTaskQueue in Phase 5.
    """

    async def enqueue(
        self,
        task_name: str,
        *_args,
        job_id: str | None = None,
        **_kwargs,
    ) -> str:
        """Log and discard the task — no background processing yet."""
        logger.debug(f"StubTaskQueue: skipping enqueue({task_name}, job_id={job_id})")
        return job_id or ""

    async def is_job_pending_or_running(self, _job_id: str) -> bool:
        """Always returns False — stub never has pending jobs."""
        return False
