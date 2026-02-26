"""Tests for AsyncioTaskQueue adapter"""

import pytest

from app.adapters.tasks.asyncio_task_queue import AsyncioTaskQueue
from app.metaclasses import Singleton


@pytest.fixture(autouse=True)
def _reset_task_queue():
    """Reset Singleton and pending jobs before each test for isolation."""
    Singleton._instances.pop(AsyncioTaskQueue, None)
    AsyncioTaskQueue._pending_jobs.clear()
    yield
    AsyncioTaskQueue._pending_jobs.clear()
    Singleton._instances.pop(AsyncioTaskQueue, None)


class TestSingleton:
    def test_same_instance_returned(self):
        q1 = AsyncioTaskQueue()
        q2 = AsyncioTaskQueue()
        assert q1 is q2

    def test_shared_pending_jobs_set(self):
        q1 = AsyncioTaskQueue()
        q2 = AsyncioTaskQueue()
        assert q1._pending_jobs is q2._pending_jobs


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_job_skipped(self):
        queue = AsyncioTaskQueue()
        await queue.enqueue("refresh", job_id="job-1")
        await queue.enqueue("refresh", job_id="job-1")
        assert len(queue._pending_jobs) == 1

    @pytest.mark.asyncio
    async def test_different_job_ids_both_recorded(self):
        queue = AsyncioTaskQueue()
        await queue.enqueue("refresh", job_id="job-a")
        await queue.enqueue("refresh", job_id="job-b")
        assert queue._pending_jobs == {"job-a", "job-b"}

    @pytest.mark.asyncio
    async def test_returns_effective_id(self):
        queue = AsyncioTaskQueue()
        result = await queue.enqueue("refresh", job_id="job-1")
        assert result == "job-1"

    @pytest.mark.asyncio
    async def test_falls_back_to_task_name_when_no_job_id(self):
        queue = AsyncioTaskQueue()
        result = await queue.enqueue("refresh_heroes")
        assert result == "refresh_heroes"
        assert "refresh_heroes" in queue._pending_jobs


class TestIsJobPendingOrRunning:
    @pytest.mark.asyncio
    async def test_pending_after_enqueue(self):
        queue = AsyncioTaskQueue()
        await queue.enqueue("refresh", job_id="job-1")
        assert await queue.is_job_pending_or_running("job-1")

    @pytest.mark.asyncio
    async def test_not_pending_for_unknown_job(self):
        queue = AsyncioTaskQueue()
        assert not await queue.is_job_pending_or_running("unknown-job")

