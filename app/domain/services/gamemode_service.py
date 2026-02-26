"""Gamemode domain service — gamemodes list"""

from app.adapters.blizzard.parsers.gamemodes import parse_gamemodes_csv
from app.config import settings
from app.domain.services.static_data_service import StaticDataService, StaticFetchConfig


class GamemodeService(StaticDataService):
    """Domain service for gamemode data."""

    async def list_gamemodes(
        self,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return the gamemodes list."""

        def _fetch() -> list[dict]:
            return parse_gamemodes_csv()

        return await self.get_or_fetch(
            StaticFetchConfig(
                storage_key="gamemodes:all",
                fetcher=_fetch,
                cache_key=cache_key,
                cache_ttl=settings.csv_cache_timeout,
                staleness_threshold=settings.gamemodes_staleness_threshold,
                entity_type="gamemodes",
            )
        )

    async def refresh_list(self) -> None:
        """Fetch fresh gamemodes list, persist to storage and update API cache.

        Called by the background worker — bypasses the SWR layer.
        """

        def _fetch() -> list[dict]:
            return parse_gamemodes_csv()

        await self._fetch_and_store(
            StaticFetchConfig(
                storage_key="gamemodes:all",
                fetcher=_fetch,
                cache_key="/gamemodes",
                cache_ttl=settings.csv_cache_timeout,
                staleness_threshold=settings.gamemodes_staleness_threshold,
                entity_type="gamemodes",
            )
        )
