"""Domain service base classes.

``BaseService`` holds infrastructure adapters and low-level helpers shared by
*all* services (static + player).

``StaticDataService`` extends it with the generic Stale-While-Revalidate flow
for data that is stored as JSON in the ``static_data`` table and where
staleness is determined by a configurable time threshold.  All static-content
services (heroes, maps, gamemodes, roles) inherit from this class.

``PlayerService`` inherits directly from ``BaseService`` and implements its own
staleness strategy (Blizzard ``lastUpdated`` comparison) and storage logic
(``player_profiles`` table).
"""

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from app.infrastructure.logger import logger

if TYPE_CHECKING:
    from app.domain.ports import (
        BlizzardClientPort,
        CachePort,
        StoragePort,
        TaskQueuePort,
    )


class StorageTable(StrEnum):
    """Persistent storage table identifiers."""

    STATIC_DATA = "static_data"
    PLAYER_PROFILES = "player_profiles"


class BaseService:
    """Infrastructure holder shared by all domain services.

    Provides:
    - Adapter references (cache, storage, blizzard_client, task_queue)
    - ``_update_api_cache``: write to Valkey after serving data
    - ``_enqueue_refresh``: deduplicated background refresh scheduling
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

    async def _update_api_cache(
        self,
        cache_key: str,
        data: Any,
        cache_ttl: int,
        *,
        staleness_threshold: int | None = None,
        stale_while_revalidate: int = 0,
    ) -> None:
        """Write data to Valkey API cache, swallowing errors."""
        try:
            await self.cache.update_api_cache(
                cache_key,
                data,
                cache_ttl,
                staleness_threshold=staleness_threshold,
                stale_while_revalidate=stale_while_revalidate,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SWR] Valkey write failed for {cache_key}: {exc}")

    async def _enqueue_refresh(
        self,
        entity_type: str,
        entity_id: str,
    ) -> None:
        """Enqueue a background refresh, deduplicating via job_id."""
        job_id = f"refresh:{entity_type}:{entity_id}"
        try:
            if not await self.task_queue.is_job_pending_or_running(job_id):
                await self.task_queue.enqueue(
                    f"refresh_{entity_type}",
                    entity_id,
                    job_id=job_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[SWR] Failed to enqueue refresh for {entity_type}/{entity_id}: {exc}"
            )
