"""Tests for BaseService — _update_api_cache and _enqueue_refresh paths"""

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.domain.services.base_service import BaseService


def _make_service(
    *,
    cache_fail: bool = False,
    queue_fail: bool = False,
    is_pending: bool = False,
) -> BaseService:
    cache = AsyncMock()
    if cache_fail:
        cache.update_api_cache.side_effect = Exception("Valkey gone")

    storage = AsyncMock()
    blizzard_client = AsyncMock()

    task_queue = AsyncMock()
    if queue_fail:
        task_queue.is_job_pending_or_running.side_effect = Exception("Queue error")
    else:
        task_queue.is_job_pending_or_running.return_value = is_pending

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
            staleness_threshold=900,
            stale_while_revalidate=60,
        )


class TestEnqueueRefresh:
    @pytest.mark.asyncio
    async def test_enqueues_when_job_not_pending(self):
        svc = _make_service(is_pending=False)
        await svc._enqueue_refresh("heroes", "heroes:en-us")
        cast("Any", svc.task_queue).enqueue.assert_awaited_once_with(
            "refresh_heroes",
            job_id="heroes:en-us",
        )

    @pytest.mark.asyncio
    async def test_skips_when_job_already_pending(self):
        svc = _make_service(is_pending=True)
        await svc._enqueue_refresh("heroes", "heroes:en-us")
        cast("Any", svc.task_queue).enqueue.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exception_is_swallowed(self):
        """Queue errors must not propagate."""
        svc = _make_service(queue_fail=True)
        # Should not raise
        await svc._enqueue_refresh("maps", "maps:all")
