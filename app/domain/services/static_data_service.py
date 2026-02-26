import inspect
import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.domain.ports.storage import StaticDataCategory
from app.domain.services import BaseService
from app.monitoring.metrics import (
    background_refresh_triggered_total,
    stale_responses_total,
    storage_hits_total,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class StaticFetchConfig:
    """Parameter object grouping all inputs needed for a static SWR fetch.

    Pass a single ``StaticFetchConfig`` to ``StaticDataService.get_or_fetch``
    instead of passing each field as a separate keyword argument.
    """

    storage_key: str
    fetcher: Callable[[], Any]
    cache_key: str
    cache_ttl: int
    staleness_threshold: int
    entity_type: str
    parser: Callable[[Any], Any] | None = field(default=None)
    result_filter: Callable[[Any], Any] | None = field(default=None)


class StaticDataService(BaseService):
    """SWR orchestration for static content backed by the ``static_data`` persistent storage table.

    Staleness is determined by a configurable time threshold.  Concrete static
    services (heroes, maps, gamemodes, roles) call ``get_or_fetch`` with a
    ``StaticFetchConfig`` — no subclass-level overrides are needed for the
    storage layer.

    Note: Valkey API-cache *reads* happen at the Nginx/Lua layer before FastAPI
    is reached; this service only ever *writes* to the API cache.
    """

    async def get_or_fetch(self, config: StaticFetchConfig) -> tuple[Any, bool, int]:
        """SWR orchestration for static data.

        Returns:
            ``(data, is_stale, age_seconds)`` tuple.  ``age_seconds`` is the
            number of seconds since the data was last stored in persistent storage (0 on
            a cold-start fetch).
        """
        stored = await self._load_from_storage(config.storage_key)
        if stored is not None:
            storage_hits_total.labels(result="hit").inc()
            return await self._serve_from_storage(stored, config)

        storage_hits_total.labels(result="miss").inc()
        return await self._cold_fetch(config)

    async def _load_from_storage(self, storage_key: str) -> dict[str, Any] | None:
        """Load raw source from the ``static_data`` table. Returns ``None`` on miss."""
        result = await self.storage.get_static_data(storage_key)
        return (
            {
                "raw": result["data"],
                "updated_at": result["updated_at"],
            }
            if result
            else None
        )

    async def _serve_from_storage(
        self, stored: dict[str, Any], config: StaticFetchConfig
    ) -> tuple[Any, bool, int]:
        """Serve data from a persistent storage hit, triggering a background refresh if stale.

        The stored ``raw`` value is always re-parsed with the current parser (for
        Blizzard HTML sources) or re-fetched from the local source (for CSV sources) so
        that code-only changes (e.g. new fields added to the parser) take effect
        immediately on restart without waiting for the staleness threshold.
        """
        data = await self._parse_stored(stored["raw"], config)
        age = int(time.time()) - stored["updated_at"]
        is_stale = age >= config.staleness_threshold
        filtered = self._apply_filter(data, config.result_filter)

        if is_stale:
            logger.info(
                f"[SWR] {config.entity_type} stale (age={age}s, "
                f"threshold={config.staleness_threshold}s) — serving + triggering refresh"
            )
            await self._enqueue_refresh(
                config.entity_type,
                config.storage_key,
            )
            stale_responses_total.inc()
            background_refresh_triggered_total.labels(
                entity_type=config.entity_type
            ).inc()
            # Short TTL absorbs burst traffic while the background refresh is in-flight.
            await self._update_api_cache(
                config.cache_key,
                filtered,
                settings.stale_cache_timeout,
                staleness_threshold=config.staleness_threshold,
                stale_while_revalidate=settings.stale_cache_timeout,
            )
        else:
            logger.info(
                f"[SWR] {config.entity_type} fresh (age={age}s) — serving from persistent storage"
            )
            await self._update_api_cache(
                config.cache_key,
                filtered,
                config.cache_ttl,
                staleness_threshold=config.staleness_threshold,
            )

        return filtered, is_stale, age

    async def _parse_stored(self, raw: str, config: StaticFetchConfig) -> Any:
        """Produce structured data from ``raw`` stored source.

        - If ``config.parser`` is set: the stored ``raw`` is HTML (or a JSON-encoded
          multi-source dict); apply the parser directly.
        - If ``config.parser`` is not set: the source is a CSV file; re-call
          ``fetcher()`` to get always-current data (fast local I/O).
        """
        if config.parser is not None:
            return config.parser(raw)

        # CSV sources: re-read from file rather than using the stored JSON.
        if inspect.iscoroutinefunction(config.fetcher):
            return await config.fetcher()
        return config.fetcher()

    @staticmethod
    def _apply_filter(data: Any, result_filter: Callable[[Any], Any] | None) -> Any:
        """Apply ``result_filter`` to ``data`` if provided, otherwise return as-is."""
        return result_filter(data) if result_filter is not None else data

    async def _fetch_and_store(self, config: StaticFetchConfig) -> Any:
        """Fetch from source, persist raw source to persistent storage, update Valkey, return filtered data."""
        if inspect.iscoroutinefunction(config.fetcher):
            raw = await config.fetcher()
        else:
            raw = config.fetcher()

        data = config.parser(raw) if config.parser is not None else raw

        # Store the raw source so re-parses on storage hits always use current parser code.
        # For HTML sources (parser set): raw is the HTML string.
        # For CSV sources (no parser): raw is already the parsed data; serialise as JSON.
        raw_to_store = (
            raw if config.parser is not None else json.dumps(raw, separators=(",", ":"))
        )
        await self._store_in_storage(
            config.storage_key, raw_to_store, config.entity_type
        )

        filtered = self._apply_filter(data, config.result_filter)
        await self._update_api_cache(
            config.cache_key,
            filtered,
            config.cache_ttl,
            staleness_threshold=config.staleness_threshold,
        )

        return filtered

    async def _cold_fetch(self, config: StaticFetchConfig) -> tuple[Any, bool, int]:
        """Fetch from source on cold start, persist to storage and Valkey."""
        logger.info(f"[SWR] {config.entity_type} not in storage — fetching from source")
        filtered = await self._fetch_and_store(config)
        return filtered, False, 0

    async def _store_in_storage(
        self, storage_key: str, raw: str, entity_type: str
    ) -> None:
        """Persist raw source string to the ``static_data`` table (zstd-compressed BYTEA)."""
        try:
            await self.storage.set_static_data(
                key=storage_key,
                data=raw,
                category=StaticDataCategory(entity_type),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SWR] Storage write failed for {storage_key}: {exc}")
