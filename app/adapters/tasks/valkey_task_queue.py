"""Valkey-backed task queue — enqueues background jobs via taskiq.

Deduplication is handled here with ``SET NX`` before dispatching to the
:class:`~app.adapters.tasks.valkey_broker.ValkeyListBroker`.  The taskiq
worker executes the tasks using FastAPI's DI container.
"""

from __future__ import annotations

from typing import Any

from app.adapters.tasks.task_registry import TASK_MAP
from app.infrastructure.logger import logger

JOB_KEY_PREFIX = "worker:job:"
JOB_TTL = 3600  # 1 hour — auto-expire stale dedup keys


class ValkeyTaskQueue:
    """Task queue that dispatches jobs to the taskiq worker via Valkey.

    Enqueue uses ``SET NX`` for deduplication: if a job-state key already
    exists the job is silently skipped.
    """

    def __init__(self, valkey_server: Any) -> None:
        self._valkey = valkey_server

    async def enqueue(
        self,
        task_name: str,
        *args: Any,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Dispatch a job to the taskiq worker, skipping duplicates.

        Uses ``SET NX`` to atomically claim the dedup slot before calling
        ``task_fn.kiq()``.  If the slot is already taken the call is a no-op.
        """
        del kwargs  # intentionally unused
        effective_id = job_id or task_name

        try:
            claimed = await self._valkey.set(
                f"{JOB_KEY_PREFIX}{effective_id}", "pending", nx=True, ex=JOB_TTL
            )
            if not claimed:
                logger.debug("[ValkeyTaskQueue] Already queued: %s", effective_id)
                return effective_id

            task_fn = TASK_MAP.get(task_name)
            if task_fn is None:
                logger.warning("[ValkeyTaskQueue] Unknown task: %r", task_name)
                return effective_id

            await task_fn.kiq(*args)
            logger.debug(
                "[ValkeyTaskQueue] Enqueued %s (job_id=%s)", task_name, effective_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ValkeyTaskQueue] Failed to enqueue %s: %s", task_name, exc)

        return effective_id

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already pending or running."""
        try:
            return (await self._valkey.exists(f"{JOB_KEY_PREFIX}{job_id}")) > 0
        except Exception:  # noqa: BLE001
            return False
