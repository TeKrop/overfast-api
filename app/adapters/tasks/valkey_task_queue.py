"""Valkey-backed task queue — enqueues background jobs using Valkey Lists."""

import json
from typing import TYPE_CHECKING, Any

from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

# Shared Valkey key names (must match valkey_worker.py)
QUEUE_KEY = "worker:queue"
JOB_KEY_PREFIX = "worker:job:"
JOB_TTL = 3600  # 1 hour — auto-expire stale job-state keys


class ValkeyTaskQueue:
    """Task queue that stores jobs in a Valkey List.

    Enqueue uses ``SET NX`` for deduplication: if a job-state key already
    exists the job is silently skipped.  The worker pops jobs from the list
    and deletes the job key when it finishes.

    ``coro``, ``on_complete``, and ``on_failure`` are accepted for interface
    compatibility with :class:`AsyncioTaskQueue` but are intentionally ignored
    — lifecycle is managed entirely by the worker process.
    """

    @property
    def _valkey(self):  # type: ignore[return]
        from app.adapters.cache.valkey_cache import ValkeyCache  # noqa: PLC0415

        return ValkeyCache().valkey_server

    async def enqueue(  # NOSONAR
        self,
        task_name: str,
        *args: Any,
        job_id: str | None = None,
        coro: Coroutine[Any, Any, Any] | None = None,
        on_complete: Callable[[str], Awaitable[None]] | None = None,
        on_failure: Callable[[str, Exception], Awaitable[None]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Push a job onto the Valkey queue, skipping duplicates.

        Uses ``SET NX`` to atomically claim the job slot before pushing.
        If the slot is already taken the job is a no-op.
        """
        del on_complete, on_failure  # intentionally unused in worker adapter
        if coro is not None:
            coro.close()  # avoid "coroutine was never awaited" warning

        effective_id = job_id or task_name

        try:
            claimed = await self._valkey.set(
                f"{JOB_KEY_PREFIX}{effective_id}", "pending", nx=True, ex=JOB_TTL
            )
            if not claimed:
                logger.debug(f"[ValkeyTaskQueue] Already queued: {effective_id}")
                return effective_id

            payload = json.dumps(
                {"task": task_name, "args": list(args), "kwargs": kwargs, "job_id": effective_id},
                separators=(",", ":"),
            )
            await self._valkey.lpush(QUEUE_KEY, payload)
            logger.debug(f"[ValkeyTaskQueue] Enqueued {task_name} (job_id={effective_id})")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ValkeyTaskQueue] Failed to enqueue {task_name}: {exc}")

        return effective_id

    async def is_job_pending_or_running(self, job_id: str) -> bool:
        """Return True if a job with this ID is already in queue or running."""
        try:
            return (await self._valkey.exists(f"{JOB_KEY_PREFIX}{job_id}")) > 0
        except Exception:  # noqa: BLE001
            return False
