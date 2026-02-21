"""Base service providing Stale-While-Revalidate orchestration for all domain services"""

import json
import time
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from app.monitoring.metrics import (
    background_refresh_triggered_total,
    stale_responses_total,
    storage_hits_total,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.domain.ports import (
        BlizzardClientPort,
        CachePort,
        StoragePort,
        TaskQueuePort,
    )


class StorageTable(StrEnum):
    """Persistent storage table identifiers used across services."""

    STATIC_DATA = "static_data"
    PLAYER_PROFILES = "player_profiles"


class BaseService:
    """Base service providing Stale-While-Revalidate (SWR) orchestration.

    The generic ``get_or_fetch`` method implements the SWR flow for data backed
    by SQLite persistent storage:

    1. Hit SQLite. If found and *fresh* → return + update Valkey.
    2. If found but *stale* → return + update Valkey + trigger background refresh.
    3. On cold start (miss) → fetch synchronously from Blizzard, store, return.

    Concrete services call ``get_or_fetch`` with domain-specific ``fetcher``,
    ``parser``, and optional ``filter`` callables.

    Note: Valkey API-cache reads happen at the Nginx/Lua layer *before* FastAPI
    is reached; services only ever *write* to the API cache.

    Player data uses a different staleness strategy (``lastUpdated`` field from
    Blizzard) so ``PlayerService`` manages its own request flow independently.
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
    # Generic SWR orchestration
    # ------------------------------------------------------------------

    async def get_or_fetch(
        self,
        *,
        storage_key: str,
        fetcher: Callable[[], Any],
        cache_key: str,
        cache_ttl: int,
        staleness_threshold: int,
        entity_type: str,
        table: StorageTable = StorageTable.STATIC_DATA,
        parser: Callable[[Any], Any] | None = None,
        result_filter: Callable[[Any], Any] | None = None,
    ) -> tuple[Any, bool]:
        """SWR orchestration for data backed by SQLite.

        Args:
            storage_key: Key in the SQLite table.
            fetcher: Async callable that retrieves raw data (HTML, JSON, or
                     any form) from the upstream source (Blizzard or local CSV).
            cache_key: Valkey API-cache key to update after serving data.
            cache_ttl: TTL in seconds for the Valkey API-cache entry.
            staleness_threshold: Seconds after which stored data is considered stale.
            entity_type: Human-readable label used in metrics / logs.
            table: SQLite table to read/write (default: static_data).
            parser: Optional callable that converts raw fetcher output into the
                    stored/returned format. Defaults to identity (raw data as-is).
            result_filter: Optional callable applied to parsed data before returning.
                    Not stored — re-applied on each request when serving stale data.

        Returns:
            ``(data, is_stale)`` tuple.
        """
        stored = await self._load_from_storage(storage_key, table)

        if stored is not None:
            data = stored["data"]
            age = int(time.time()) - stored["updated_at"]
            is_stale = age >= staleness_threshold

            if is_stale:
                logger.info(
                    f"[SWR] {entity_type} stale (age={age}s, "
                    f"threshold={staleness_threshold}s) — serving + triggering refresh"
                )
                await self._enqueue_refresh(entity_type, storage_key)
                stale_responses_total.inc()
                background_refresh_triggered_total.labels(entity_type=entity_type).inc()
            else:
                logger.info(
                    f"[SWR] {entity_type} fresh (age={age}s) — serving from SQLite"
                )

            storage_hits_total.labels(result="hit").inc()

            if result_filter is not None:
                data = result_filter(data)

            await self._update_api_cache(cache_key, data, cache_ttl)
            return data, is_stale

        # Cold start — fetch synchronously
        logger.info(f"[SWR] {entity_type} not in SQLite — fetching from source")
        storage_hits_total.labels(result="miss").inc()

        raw = await fetcher()
        data = parser(raw) if parser is not None else raw
        await self._store_in_storage(storage_key, data, table)

        filtered = result_filter(data) if result_filter is not None else data
        await self._update_api_cache(cache_key, filtered, cache_ttl)
        return filtered, False

    # ------------------------------------------------------------------
    # Storage helpers — overridable by concrete services
    # ------------------------------------------------------------------

    async def _load_from_storage(
        self, storage_key: str, table: StorageTable
    ) -> dict[str, Any] | None:
        """Load data from the given SQLite table. Returns ``None`` on miss."""
        if table == StorageTable.STATIC_DATA:
            result = await self.storage.get_static_data(storage_key)
            if result:
                return {
                    "data": json.loads(result["data"]),
                    "updated_at": result["updated_at"],
                }
        return None

    async def _store_in_storage(
        self, storage_key: str, data: Any, table: StorageTable
    ) -> None:
        """Persist data to the given SQLite table (default: static_data JSON)."""
        if table == StorageTable.STATIC_DATA:
            try:
                await self.storage.set_static_data(
                    key=storage_key,
                    data=json.dumps(data, separators=(",", ":")),
                    data_type="json",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[SWR] SQLite write failed for {storage_key}: {exc}")

    # ------------------------------------------------------------------
    # Shared low-level helpers
    # ------------------------------------------------------------------

    async def _update_api_cache(
        self, cache_key: str, data: Any, cache_ttl: int
    ) -> None:
        """Write data to Valkey API cache, swallowing errors."""
        try:
            await self.cache.update_api_cache(cache_key, data, cache_ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SWR] Valkey write failed for {cache_key}: {exc}")

    async def _enqueue_refresh(self, entity_type: str, entity_id: str) -> None:
        """Enqueue a background refresh, deduplicating via job_id."""
        job_id = f"refresh:{entity_type}:{entity_id}"
        try:
            already_running = await self.task_queue.is_job_pending_or_running(job_id)
            if not already_running:
                await self.task_queue.enqueue(
                    f"refresh_{entity_type}",
                    entity_id,
                    job_id=job_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[SWR] Failed to enqueue refresh for {entity_type}/{entity_id}: {exc}"
            )
