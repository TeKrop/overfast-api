"""Tests for BaseService — _update_api_cache and _enqueue_refresh paths"""

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.domain.services.base_service import BaseService


def _make_service(
    *,
    cache_fail: bool = False,
    queue_fail: bool = False,
) -> BaseService:
    cache = AsyncMock()
    if cache_fail:
        cache.update_api_cache.side_effect = Exception("Valkey gone")

    storage = AsyncMock()
    blizzard_client = AsyncMock()

    task_queue = AsyncMock()
    if queue_fail:
        task_queue.enqueue.side_effect = Exception("Queue error")

    return BaseService(cache, storage, blizzard_client, task_queue)


class TestUpdateApiCache:
    @pytest.mark.asyncio
    async def test_success_calls_cache(self):
        svc = _make_service()
        await svc._update_api_cache("my-key", {"data": 1}, 3600)
        cast("Any", svc.cache).update_api_cache.assert_awaited_once_with(
            "my-key",
            {"data": 1},
            3600,
            stored_at=None,
            staleness_threshold=None,
            stale_while_revalidate=0,
        )

    @pytest.mark.asyncio
    async def test_exception_is_swallowed(self):
        """Valkey write errors must not propagate."""
        svc = _make_service(cache_fail=True)
        # Should not raise
        await svc._update_api_cache("key", {}, 600)

    @pytest.mark.asyncio
    async def test_staleness_threshold_forwarded(self):
        svc = _make_service()
        await svc._update_api_cache(
            "key",
            [],
            1800,
            staleness_threshold=900,
            stale_while_revalidate=60,
        )
        cast("Any", svc.cache).update_api_cache.assert_awaited_once_with(
            "key",
            [],
            1800,
            stored_at=None,
            staleness_threshold=900,
            stale_while_revalidate=60,
        )

    @pytest.mark.asyncio
    async def test_stored_at_forwarded(self):
        """stored_at is forwarded verbatim so Age is preserved across SWR rewrites."""
        svc = _make_service()
        await svc._update_api_cache("key", [], 86400, stored_at=1_000_000)
        cast("Any", svc.cache).update_api_cache.assert_awaited_once_with(
            "key",
            [],
            86400,
            stored_at=1_000_000,
            staleness_threshold=None,
            stale_while_revalidate=0,
        )


class TestEnqueueRefresh:
    @pytest.mark.asyncio
    async def test_enqueues_the_refresh(self):
        svc = _make_service()
        await svc._enqueue_refresh("heroes", "heroes:en-us")
        cast("Any", svc.task_queue).enqueue.assert_awaited_once_with(
            "refresh_heroes",
            job_id="heroes:en-us",
        )

    @pytest.mark.asyncio
    async def test_does_not_pre_check_for_a_pending_job(self):
        """Deduplication belongs to the queue, which claims with SET NX.

        Asking first cost an extra round-trip on every stale read and left a
        window for another process to claim in between. See
        tests/adapters/tasks/test_valkey_task_queue.py::test_duplicate_job_skipped
        for the dedup itself.
        """
        svc = _make_service()
        await svc._enqueue_refresh("heroes", "heroes:en-us")
        cast("Any", svc.task_queue).is_job_pending_or_running.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exception_is_swallowed(self):
        """Queue errors must not propagate."""
        svc = _make_service(queue_fail=True)
        # Should not raise
        await svc._enqueue_refresh("maps", "maps:all")
