"""Tests for ValkeyTaskQueue adapter"""

import fakeredis
import pytest

from app.adapters.tasks.valkey_task_queue import ValkeyTaskQueue


@pytest.fixture
def fake_redis() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis(protocol=3)


@pytest.fixture
def queue(fake_redis: fakeredis.FakeAsyncRedis) -> ValkeyTaskQueue:
    return ValkeyTaskQueue(fake_redis)


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_job_skipped(self, queue: ValkeyTaskQueue):
        await queue.enqueue("refresh", job_id="job-1")
        await queue.enqueue("refresh", job_id="job-1")
        # Only one key should exist in redis
        assert await queue.is_job_pending_or_running("job-1")

    @pytest.mark.asyncio
    async def test_different_job_ids_both_recorded(self, queue: ValkeyTaskQueue):
        await queue.enqueue("refresh", job_id="job-a")
        await queue.enqueue("refresh", job_id="job-b")
        assert await queue.is_job_pending_or_running("job-a")
        assert await queue.is_job_pending_or_running("job-b")

    @pytest.mark.asyncio
    async def test_returns_effective_id(self, queue: ValkeyTaskQueue):
        result = await queue.enqueue("refresh", job_id="job-1")
        assert result == "job-1"

    @pytest.mark.asyncio
    async def test_falls_back_to_task_name_when_no_job_id(self, queue: ValkeyTaskQueue):
        result = await queue.enqueue("refresh_heroes")
        assert result == "refresh_heroes"
        assert await queue.is_job_pending_or_running("refresh_heroes")


class TestIsJobPendingOrRunning:
    @pytest.mark.asyncio
    async def test_pending_after_enqueue(self, queue: ValkeyTaskQueue):
        await queue.enqueue("refresh", job_id="job-1")
        assert await queue.is_job_pending_or_running("job-1")

    @pytest.mark.asyncio
    async def test_not_pending_for_unknown_job(self, queue: ValkeyTaskQueue):
        assert not await queue.is_job_pending_or_running("unknown-job")

    @pytest.mark.asyncio
    async def test_independent_instances_share_redis_state(
        self, fake_redis: fakeredis.FakeAsyncRedis
    ):
        """Two queue instances using the same redis see each other's dedup keys."""
        q1 = ValkeyTaskQueue(fake_redis)
        q2 = ValkeyTaskQueue(fake_redis)
        await q1.enqueue("refresh", job_id="job-shared")
        assert await q2.is_job_pending_or_running("job-shared")
