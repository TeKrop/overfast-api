import json
import time
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.domain.services import BaseService
from app.monitoring.metrics import (
    background_refresh_triggered_total,
    stale_responses_total,
    storage_hits_total,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable


class StaticDataService(BaseService):
    """SWR orchestration for static content backed by the ``static_data`` SQLite table.

    Staleness is determined by a configurable time threshold.  Concrete static
    services (heroes, maps, gamemodes, roles) call ``get_or_fetch`` with
    domain-specific ``fetcher``, ``parser``, and optional ``result_filter``
    callables — no subclass-level overrides are needed for the storage layer.

    Note: Valkey API-cache *reads* happen at the Nginx/Lua layer before FastAPI
    is reached; this service only ever *writes* to the API cache.
    """

    async def get_or_fetch(
        self,
        *,
        storage_key: str,
        fetcher: Callable[[], Any],
        cache_key: str,
        cache_ttl: int,
        staleness_threshold: int,
        entity_type: str,
        parser: Callable[[Any], Any] | None = None,
        result_filter: Callable[[Any], Any] | None = None,
    ) -> tuple[Any, bool, int]:
        """SWR orchestration for static data.

        Args:
            storage_key: Key in the ``static_data`` SQLite table.
            fetcher: Async callable that retrieves raw data from the upstream
                     source (Blizzard HTML/JSON or a local CSV file).
            cache_key: Valkey API-cache key to update after serving data.
            cache_ttl: TTL in seconds for the Valkey API-cache entry.
            staleness_threshold: Seconds after which stored data is considered stale.
            entity_type: Human-readable label used in metrics and logs.
            parser: Optional callable that converts raw fetcher output into the
                    stored/returned format.  Defaults to identity (raw data as-is).
            result_filter: Optional callable applied to the stored data before
                    returning.  Not persisted — re-applied on every request.

        Returns:
            ``(data, is_stale, age_seconds)`` tuple.  ``age_seconds`` is the
            number of seconds since the data was last stored in SQLite (0 on
            a cold-start fetch).
        """
        stored = await self._load_from_storage(storage_key)
        if stored is not None:
            storage_hits_total.labels(result="hit").inc()
            return await self._serve_from_storage(
                stored,
                storage_key=storage_key,
                fetcher=fetcher,
                parser=parser,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
                staleness_threshold=staleness_threshold,
                entity_type=entity_type,
                result_filter=result_filter,
            )

        storage_hits_total.labels(result="miss").inc()
        return await self._cold_fetch(
            storage_key=storage_key,
            fetcher=fetcher,
            parser=parser,
            cache_key=cache_key,
            cache_ttl=cache_ttl,
            entity_type=entity_type,
            result_filter=result_filter,
        )

    async def _serve_from_storage(
        self,
        stored: dict[str, Any],
        *,
        storage_key: str,
        fetcher: Callable[[], Any],
        parser: Callable[[Any], Any] | None,
        cache_key: str,
        cache_ttl: int,
        staleness_threshold: int,
        entity_type: str,
        result_filter: Callable[[Any], Any] | None,
    ) -> tuple[Any, bool, int]:
        """Serve data from a SQLite hit, triggering a background refresh if stale."""
        data = stored["data"]
        age = int(time.time()) - stored["updated_at"]
        is_stale = age >= staleness_threshold
        filtered = self._apply_filter(data, result_filter)

        if is_stale:
            logger.info(
                f"[SWR] {entity_type} stale (age={age}s, "
                f"threshold={staleness_threshold}s) — serving + triggering refresh"
            )
            await self._enqueue_refresh(
                entity_type,
                storage_key,
                refresh_coro=self._refresh_static(
                    storage_key,
                    fetcher,
                    parser,
                    entity_type,
                    cache_key=cache_key,
                    cache_ttl=cache_ttl,
                    result_filter=result_filter,
                ),
            )
            stale_responses_total.inc()
            background_refresh_triggered_total.labels(entity_type=entity_type).inc()
            # Short TTL absorbs burst traffic while the background refresh is in-flight.
            await self._update_api_cache(
                cache_key, filtered, settings.stale_cache_timeout
            )
        else:
            logger.info(f"[SWR] {entity_type} fresh (age={age}s) — serving from SQLite")
            await self._update_api_cache(cache_key, filtered, cache_ttl)

        return filtered, is_stale, age

    async def _cold_fetch(
        self,
        *,
        storage_key: str,
        fetcher: Callable[[], Any],
        parser: Callable[[Any], Any] | None,
        cache_key: str,
        cache_ttl: int,
        entity_type: str,
        result_filter: Callable[[Any], Any] | None,
    ) -> tuple[Any, bool, int]:
        """Fetch from source on cold start, persist to SQLite and Valkey."""
        logger.info(f"[SWR] {entity_type} not in SQLite — fetching from source")
        filtered = await self._fetch_and_store(
            storage_key=storage_key,
            fetcher=fetcher,
            parser=parser,
            cache_key=cache_key,
            cache_ttl=cache_ttl,
            result_filter=result_filter,
        )
        return filtered, False, 0

    async def _fetch_and_store(
        self,
        *,
        storage_key: str,
        fetcher: Callable[[], Any],
        parser: Callable[[Any], Any] | None,
        cache_key: str,
        cache_ttl: int,
        result_filter: Callable[[Any], Any] | None,
    ) -> Any:
        """Fetch from source, persist to SQLite, update Valkey, return filtered data."""
        raw = await fetcher()
        data = parser(raw) if parser is not None else raw
        await self._store_in_storage(storage_key, data)
        filtered = self._apply_filter(data, result_filter)
        await self._update_api_cache(cache_key, filtered, cache_ttl)
        return filtered

    @staticmethod
    def _apply_filter(data: Any, result_filter: Callable[[Any], Any] | None) -> Any:
        """Apply ``result_filter`` to ``data`` if provided, otherwise return as-is."""
        return result_filter(data) if result_filter is not None else data

    async def _refresh_static(
        self,
        storage_key: str,
        fetcher: Callable[[], Any],
        parser: Callable[[Any], Any] | None,
        entity_type: str,
        *,
        cache_key: str,
        cache_ttl: int,
        result_filter: Callable[[Any], Any] | None = None,
    ) -> None:
        """Fetch fresh data, persist to SQLite and update Valkey with full TTL."""
        logger.info(f"[SWR] Background refresh started for {entity_type}/{storage_key}")
        try:
            await self._fetch_and_store(
                storage_key=storage_key,
                fetcher=fetcher,
                parser=parser,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
                result_filter=result_filter,
            )
            logger.info(
                f"[SWR] Background refresh complete for {entity_type}/{storage_key}"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[SWR] Background refresh failed for {entity_type}/{storage_key}: {exc}"
            )

    async def _load_from_storage(self, storage_key: str) -> dict[str, Any] | None:
        """Load data from the ``static_data`` SQLite table. Returns ``None`` on miss."""
        result = await self.storage.get_static_data(storage_key)
        return (
            {
                "data": json.loads(result["data"]),
                "updated_at": result["updated_at"],
            }
            if result
            else None
        )

    async def _store_in_storage(self, storage_key: str, data: Any) -> None:
        """Persist data to the ``static_data`` SQLite table as JSON."""
        try:
            await self.storage.set_static_data(
                key=storage_key,
                data=json.dumps(data, separators=(",", ":")),
                data_type="json",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SWR] SQLite write failed for {storage_key}: {exc}")
