"""Map domain service — maps list"""

from app.adapters.blizzard.parsers.maps import parse_maps_csv
from app.config import settings
from app.domain.services.base_service import BaseService


class MapService(BaseService):
    """Domain service for maps data."""

    async def list_maps(
        self,
        gamemode: str | None,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return the maps list (with optional gamemode filter).

        Stores the full (unfiltered) maps list in SQLite; gamemode filter is
        applied after retrieval.

        Returns:
            (data, is_stale, age_seconds)
        """
        storage_key = "maps:all"

        async def _fetch() -> list[dict]:
            return parse_maps_csv()

        data, is_stale, age = await self._get_or_fetch_static(
            storage_key=storage_key,
            fetcher=_fetch,
            cache_key=cache_key,
            cache_ttl=settings.csv_cache_timeout,
            staleness_threshold=settings.maps_staleness_threshold,
            entity_type="maps",
        )

        if gamemode:
            gamemode_val = gamemode.value if hasattr(gamemode, "value") else gamemode
            data = [m for m in data if gamemode_val in m.get("gamemodes", [])]

        return data, is_stale, age
