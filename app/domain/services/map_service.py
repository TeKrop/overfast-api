"""Map domain service — maps list"""

from app.adapters.blizzard.parsers.maps import parse_maps_csv
from app.config import settings
from app.domain.services.static_data_service import StaticDataService, StaticFetchConfig


class MapService(StaticDataService):
    """Domain service for maps data."""

    def _maps_config(
        self, cache_key: str, gamemode: str | None = None
    ) -> StaticFetchConfig:
        """Build a StaticFetchConfig for the maps list."""

        def _fetch() -> list[dict]:
            return parse_maps_csv()

        def _filter(data: list[dict]) -> list[dict]:
            if not gamemode:
                return data
            gamemode_val = gamemode.value if hasattr(gamemode, "value") else gamemode
            return [m for m in data if gamemode_val in m.get("gamemodes", [])]

        return StaticFetchConfig(
            storage_key="maps:all",
            fetcher=_fetch,
            result_filter=_filter if gamemode else None,
            cache_key=cache_key,
            cache_ttl=settings.csv_cache_timeout,
            staleness_threshold=settings.maps_staleness_threshold,
            entity_type="maps",
        )

    async def list_maps(
        self,
        gamemode: str | None,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return the maps list (with optional gamemode filter).

        Stores the full (unfiltered) maps list in persistent storage.
        """
        return await self.get_or_fetch(self._maps_config(cache_key, gamemode))

    async def refresh_list(self) -> None:
        """Fetch fresh maps list, persist to storage and update API cache.

        Called by the background worker — bypasses the SWR layer.
        """
        await self._fetch_and_store(self._maps_config("/maps"))
