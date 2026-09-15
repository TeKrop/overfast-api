"""Tests for ValkeyTaskQueue adapter"""

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest

from app.adapters.tasks.valkey_broker import broker
from app.adapters.tasks.valkey_task_queue import ValkeyTaskQueue
from app.config import settings

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def fake_redis() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis(protocol=3)


@pytest.fixture
def queue(fake_redis: fakeredis.FakeAsyncRedis) -> ValkeyTaskQueue:
    return ValkeyTaskQueue(fake_redis)


@pytest.fixture
def kicker() -> Iterator[MagicMock]:
    """Patch taskiq's AsyncKicker; ``kicker.return_value.kiq`` is the dispatch call."""
    with patch("app.adapters.tasks.valkey_task_queue.AsyncKicker") as mock_kicker:
        mock_kicker.return_value.kiq = AsyncMock()
        yield mock_kicker


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_job_skipped(
        self, queue: ValkeyTaskQueue, kicker: MagicMock
    ):
        await queue.enqueue("refresh", job_id="job-1")
        await queue.enqueue("refresh", job_id="job-1")

        kicker.return_value.kiq.assert_awaited_once_with("job-1")

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("kicker")
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
    @pytest.mark.usefixtures("kicker")
    async def test_falls_back_to_task_name_when_no_job_id(self, queue: ValkeyTaskQueue):
        result = await queue.enqueue("refresh_heroes")

        pending = await queue.is_job_pending_or_running("refresh_heroes")

        assert result == "refresh_heroes"
        assert pending


class TestIsJobPendingOrRunning:
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("kicker")
    async def test_pending_after_enqueue(self, queue: ValkeyTaskQueue):
        await queue.enqueue("refresh", job_id="job-1")

        result = await queue.is_job_pending_or_running("job-1")

        assert result

    @pytest.mark.asyncio
    async def test_not_pending_for_unknown_job(self, queue: ValkeyTaskQueue):
        result = await queue.is_job_pending_or_running("unknown-job")

        assert not result

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("kicker")
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
    async def test_task_kicked_by_name(self, queue: ValkeyTaskQueue, kicker: MagicMock):
        """The task is kicked by name on the shared broker with the effective_id."""
        await queue.enqueue("refresh_heroes", job_id="heroes")

        kicker.assert_called_once_with("refresh_heroes", broker, {})
        kicker.return_value.kiq.assert_awaited_once_with("heroes")

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("kicker")
    async def test_dispatch_records_refresh_metric(self, queue: ValkeyTaskQueue):
        """Only dispatched jobs are counted, labelled by entity type."""
        with (
            patch.object(settings, "prometheus_enabled", True),
            patch(
                "app.adapters.tasks.valkey_task_queue.background_refresh_triggered_total"
            ) as m_refresh,
        ):
            await queue.enqueue("refresh_heroes", job_id="heroes")
            await queue.enqueue("refresh_heroes", job_id="heroes")

        m_refresh.labels.assert_called_once_with(entity_type="heroes")

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


class TestReleaseJob:
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("kicker")
    async def test_release_removes_dedup_key(self, queue: ValkeyTaskQueue):
        """After release_job, is_job_pending_or_running returns False."""
        await queue.enqueue("refresh", job_id="job-1")

        await queue.release_job("job-1")

        result = await queue.is_job_pending_or_running("job-1")
        assert not result

    @pytest.mark.asyncio
    async def test_release_allows_reenqueue(
        self, queue: ValkeyTaskQueue, kicker: MagicMock
    ):
        """After release_job the same job_id can be dispatched again."""
        await queue.enqueue("refresh", job_id="job-1")
        await queue.release_job("job-1")
        await queue.enqueue("refresh", job_id="job-1")

        assert kicker.return_value.kiq.await_count == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_release_nonexistent_job_is_noop(self, queue: ValkeyTaskQueue):
        """Releasing an unknown job_id does not raise."""
        await queue.release_job("nonexistent-job")

    @pytest.mark.asyncio
    async def test_redis_exception_is_swallowed(
        self, fake_redis: fakeredis.FakeAsyncRedis
    ):
        """If redis raises during release, the exception is swallowed."""
        queue = ValkeyTaskQueue(fake_redis)
        cast("Any", fake_redis).delete = AsyncMock(
            side_effect=RuntimeError("redis down")
        )
        await queue.release_job("any-job")
