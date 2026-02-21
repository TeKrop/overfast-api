"""Gamemode domain service — gamemodes list"""

from app.adapters.blizzard.parsers.gamemodes import parse_gamemodes_csv
from app.config import settings
from app.domain.services.base_service import BaseService


class GamemodeService(BaseService):
    """Domain service for gamemode data."""

    async def list_gamemodes(
        self,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return the gamemodes list.

        Returns:
            (data, is_stale, age_seconds)
        """
        storage_key = "gamemodes:all"

        async def _fetch() -> list[dict]:
            return parse_gamemodes_csv()

        return await self._get_or_fetch_static(
            storage_key=storage_key,
            fetcher=_fetch,
            cache_key=cache_key,
            cache_ttl=settings.csv_cache_timeout,
            staleness_threshold=settings.gamemodes_staleness_threshold,
            entity_type="gamemodes",
        )
