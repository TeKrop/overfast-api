"""Tests for ValkeyTaskQueue adapter"""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

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
        result = await queue.is_job_pending_or_running("job-1")

        assert result

    @pytest.mark.asyncio
    async def test_different_job_ids_both_recorded(self, queue: ValkeyTaskQueue):
        await queue.enqueue("refresh", job_id="job-a")
        await queue.enqueue("refresh", job_id="job-b")

        result_a = await queue.is_job_pending_or_running("job-a")
        result_b = await queue.is_job_pending_or_running("job-b")

        assert result_a
        assert result_b

    @pytest.mark.asyncio
    async def test_returns_effective_id(self, queue: ValkeyTaskQueue):
        result = await queue.enqueue("refresh", job_id="job-1")

        assert result == "job-1"

    @pytest.mark.asyncio
    async def test_falls_back_to_task_name_when_no_job_id(self, queue: ValkeyTaskQueue):
        result = await queue.enqueue("refresh_heroes")

        pending = await queue.is_job_pending_or_running("refresh_heroes")

        assert result == "refresh_heroes"
        assert pending


class TestIsJobPendingOrRunning:
    @pytest.mark.asyncio
    async def test_pending_after_enqueue(self, queue: ValkeyTaskQueue):
        await queue.enqueue("refresh", job_id="job-1")

        result = await queue.is_job_pending_or_running("job-1")

        assert result

    @pytest.mark.asyncio
    async def test_not_pending_for_unknown_job(self, queue: ValkeyTaskQueue):
        result = await queue.is_job_pending_or_running("unknown-job")

        assert not result

    @pytest.mark.asyncio
    async def test_independent_instances_share_redis_state(
        self, fake_redis: fakeredis.FakeAsyncRedis
    ):
        """Two queue instances using the same redis see each other's dedup keys."""
        q1 = ValkeyTaskQueue(fake_redis)
        q2 = ValkeyTaskQueue(fake_redis)
        await q1.enqueue("refresh", job_id="job-shared")

        result = await q2.is_job_pending_or_running("job-shared")

        assert result


class TestEnqueueTaskDispatch:
    @pytest.mark.asyncio
    async def test_known_task_kiq_called(self, queue: ValkeyTaskQueue):
        """A known task name triggers task_fn.kiq(effective_id)."""
        mock_task = MagicMock()
        mock_task.kiq = AsyncMock()
        with patch.dict(
            "app.adapters.tasks.valkey_task_queue.TASK_MAP",
            {"refresh_heroes": mock_task},
        ):
            await queue.enqueue("refresh_heroes", job_id="heroes")
        mock_task.kiq.assert_awaited_once_with("heroes")

    @pytest.mark.asyncio
    async def test_unknown_task_skips_kiq(self, queue: ValkeyTaskQueue):
        """An unknown task name is a no-op (logs warning, returns effective_id)."""
        result = await queue.enqueue("nonexistent_task", job_id="xyz")

        pending = await queue.is_job_pending_or_running("xyz")

        assert result == "xyz"
        assert pending

    @pytest.mark.asyncio
    async def test_redis_exception_is_swallowed(
        self, fake_redis: fakeredis.FakeAsyncRedis
    ):
        """If redis raises, enqueue swallows the exception and returns effective_id."""
        queue = ValkeyTaskQueue(fake_redis)
        cast("Any", fake_redis).set = AsyncMock(side_effect=RuntimeError("redis down"))
        result = await queue.enqueue("refresh_heroes", job_id="boom")

        assert result == "boom"


class TestIsJobPendingOrRunningExceptionHandling:
    @pytest.mark.asyncio
    async def test_redis_exception_returns_false(
        self, fake_redis: fakeredis.FakeAsyncRedis
    ):
        """If redis raises, is_job_pending_or_running returns False."""
        queue = ValkeyTaskQueue(fake_redis)
        cast("Any", fake_redis).exists = AsyncMock(
            side_effect=RuntimeError("redis down")
        )
        result = await queue.is_job_pending_or_running("any-job")

        assert result is False
