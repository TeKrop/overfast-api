"""Base service providing Stale-While-Revalidate orchestration for all domain services"""

import json
import time
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.domain.ports import (
        BlizzardClientPort,
        CachePort,
        StoragePort,
        TaskQueuePort,
    )


class BaseService:
    """Base service providing Stale-While-Revalidate (SWR) orchestration.

    All domain services inherit from this class to get SWR behaviour:
    1. Check SQLite persistent storage (cache key).
    2. If found and fresh (age < staleness_threshold) → return data, update Valkey.
    3. If found but stale → return data, update Valkey, trigger background refresh.
    4. If not found (cold start) → fetch from Blizzard, store in both, return data.

    Note: Valkey API-cache check happens at the Nginx/Lua level before FastAPI is reached,
    so this class only handles the SQLite → Blizzard fallback path.
    """

    def __init__(
        self,
        cache: CachePort,
        storage: StoragePort,
        blizzard_client: BlizzardClientPort,
        task_queue: TaskQueuePort,
    ) -> None:
        self.cache = cache
        self.storage = storage
        self.blizzard_client = blizzard_client
        self.task_queue = task_queue

    # ------------------------------------------------------------------
    # SWR core — used by static-data services (heroes, maps, …)
    # ------------------------------------------------------------------

    async def _get_or_fetch_static(
        self,
        *,
        storage_key: str,
        fetcher: Callable[[], Awaitable[Any]],
        cache_key: str,
        cache_ttl: int,
        staleness_threshold: int,
        entity_type: str,
    ) -> tuple[Any, bool, int]:
        """SWR orchestration for static data backed by SQLite.

        Args:
            storage_key: Key in the ``static_data`` SQLite table.
            fetcher: Async callable that fetches and parses fresh data from Blizzard.
                     Must return the final *list* or *dict* to store as JSON.
            cache_key: Valkey API-cache key to update after serving data.
            cache_ttl: TTL in seconds for the Valkey API-cache entry.
            staleness_threshold: Seconds after which stored data is considered stale.
            entity_type: Human-readable label used in metrics / logs.

        Returns:
            ``(data, is_stale, age_seconds)`` tuple.
            ``age_seconds`` is 0 on a cold-start fetch.
        """
        stored = await self.storage.get_static_data(storage_key)

        if stored:
            data = json.loads(stored["data"])
            age = int(time.time()) - stored["updated_at"]
            is_stale = age >= staleness_threshold

            if is_stale:
                logger.info(
                    f"[SWR] {entity_type} data is stale (age={age}s, "
                    f"threshold={staleness_threshold}s) — serving stale + triggering refresh"
                )
                await self._enqueue_refresh(entity_type, storage_key)
                self._track_stale_response(entity_type)
            else:
                logger.info(
                    f"[SWR] {entity_type} data is fresh (age={age}s) — serving from SQLite"
                )

            self._track_storage_hit("hit")
            await self._update_api_cache(cache_key, data, cache_ttl)
            return data, is_stale, age

        # Cold start — fetch synchronously from Blizzard
        logger.info(f"[SWR] {entity_type} not in SQLite — fetching from Blizzard")
        self._track_storage_hit("miss")
        data = await fetcher()
        await self._persist_static(storage_key, data, cache_key, cache_ttl)
        return data, False, 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _persist_static(
        self, storage_key: str, data: Any, cache_key: str, cache_ttl: int
    ) -> None:
        """Write static data to both SQLite and Valkey API cache."""
        try:
            await self.storage.set_static_data(
                key=storage_key,
                data=json.dumps(data, separators=(",", ":")),
                data_type="json",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SWR] SQLite write failed for {storage_key}: {exc}")

        await self._update_api_cache(cache_key, data, cache_ttl)

    async def _update_api_cache(
        self, cache_key: str, data: Any, cache_ttl: int
    ) -> None:
        """Write data to Valkey API cache, swallowing errors."""
        try:
            await self.cache.update_api_cache(cache_key, data, cache_ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SWR] Valkey write failed for {cache_key}: {exc}")

    async def _enqueue_refresh(self, entity_type: str, entity_id: str) -> None:
        """Enqueue a background refresh task (deduplication via job_id)."""
        job_id = f"refresh:{entity_type}:{entity_id}"
        try:
            already_running = await self.task_queue.is_job_pending_or_running(job_id)
            if not already_running:
                await self.task_queue.enqueue(
                    f"refresh_{entity_type}",
                    entity_id,
                    job_id=job_id,
                )
                if settings.prometheus_enabled:
                    from app.monitoring.metrics import (
                        background_refresh_triggered_total,
                    )

                    background_refresh_triggered_total.labels(
                        entity_type=entity_type
                    ).inc()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[SWR] Failed to enqueue refresh for {entity_type}/{entity_id}: {exc}"
            )

    @staticmethod
    def _track_storage_hit(result: str) -> None:
        if settings.prometheus_enabled:
            from app.monitoring.metrics import storage_hits_total

            storage_hits_total.labels(result=result).inc()

    @staticmethod
    def _track_stale_response(entity_type: str) -> None:
        if settings.prometheus_enabled:
            from app.monitoring.metrics import stale_responses_total

            stale_responses_total.inc()
            # entity_type tracked via background_refresh_triggered_total
            _ = entity_type
