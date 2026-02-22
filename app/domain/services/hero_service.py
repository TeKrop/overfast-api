"""Hero domain service — heroes list, hero detail, hero stats"""

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from app.adapters.blizzard.parsers.hero import parse_hero
from app.adapters.blizzard.parsers.hero_stats_summary import parse_hero_stats_summary
from app.adapters.blizzard.parsers.heroes import (
    fetch_heroes_html,
    filter_heroes,
    parse_heroes_html,
)
from app.adapters.blizzard.parsers.heroes_hitpoints import parse_heroes_hitpoints
from app.config import settings
from app.domain.services.static_data_service import StaticDataService, StaticFetchConfig
from app.enums import Locale
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error

if TYPE_CHECKING:
    from app.heroes.enums import HeroGamemode
    from app.maps.enums import MapKey
    from app.players.enums import (
        CompetitiveDivisionFilter,
        PlayerGamemode,
        PlayerPlatform,
        PlayerRegion,
    )
    from app.roles.enums import Role


class HeroService(StaticDataService):
    """Domain service for hero data: list, detail, and usage statistics."""

    # ------------------------------------------------------------------
    # Heroes list  (GET /heroes)
    # ------------------------------------------------------------------

    async def list_heroes(
        self,
        locale: Locale,
        role: Role | None,
        gamemode: HeroGamemode | None,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return the heroes list (with optional role/gamemode filters).

        Stores the *full* (unfiltered) heroes list per locale in SQLite so
        that all filter combinations benefit from the same cache entry.
        """

        async def _fetch() -> list[dict]:
            html = await fetch_heroes_html(self.blizzard_client, locale)
            return parse_heroes_html(html)

        def _filter(data: list[dict]) -> list[dict]:
            return filter_heroes(data, role, gamemode)

        return await self.get_or_fetch(
            StaticFetchConfig(
                storage_key=f"heroes:{locale}",
                fetcher=_fetch,
                result_filter=_filter,
                cache_key=cache_key,
                cache_ttl=settings.heroes_path_cache_timeout,
                staleness_threshold=settings.heroes_staleness_threshold,
                entity_type="heroes",
            )
        )

    # ------------------------------------------------------------------
    # Single hero  (GET /heroes/{hero_key})
    # ------------------------------------------------------------------

    async def get_hero(
        self,
        hero_key: str,
        locale: Locale,
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return full hero details merged with portrait and hitpoints.

        Stores the merged hero data per ``hero_key:locale`` in SQLite so that
        subsequent requests benefit from the SWR cache and background refresh.
        """

        async def _fetch() -> dict:
            try:
                hero_data = await parse_hero(self.blizzard_client, hero_key, locale)
                heroes_html = await fetch_heroes_html(self.blizzard_client, locale)
                heroes_list = parse_heroes_html(heroes_html)
                heroes_hitpoints = parse_heroes_hitpoints()
                return _merge_hero_data(
                    hero_data, heroes_list, heroes_hitpoints, hero_key
                )
            except ParserBlizzardError as exc:
                raise HTTPException(
                    status_code=exc.status_code, detail=exc.message
                ) from exc
            except ParserParsingError as exc:
                blizzard_url = f"{settings.blizzard_host}/{locale}{settings.heroes_path}{hero_key}/"
                raise overfast_internal_error(blizzard_url, exc) from exc

        return await self.get_or_fetch(
            StaticFetchConfig(
                storage_key=f"hero:{hero_key}:{locale}",
                fetcher=_fetch,
                cache_key=cache_key,
                cache_ttl=settings.hero_path_cache_timeout,
                staleness_threshold=settings.heroes_staleness_threshold,
                entity_type="hero",
            )
        )

    # ------------------------------------------------------------------
    # Hero stats summary  (GET /heroes/stats)
    # ------------------------------------------------------------------

    async def get_hero_stats(
        self,
        platform: PlayerPlatform,
        gamemode: PlayerGamemode,
        region: PlayerRegion,
        role: Role | None,
        map_filter: MapKey | None,  # ty: ignore[invalid-type-form]
        competitive_division: CompetitiveDivisionFilter | None,  # ty: ignore[invalid-type-form]
        order_by: str,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return hero usage statistics — Valkey-only cache, no persistent storage.

        Stats change frequently and have too many parameter combinations to
        store in SQLite. The Valkey API cache (populated here, served by nginx)
        is sufficient.
        """
        try:
            data = await parse_hero_stats_summary(
                self.blizzard_client,
                platform=platform,
                gamemode=gamemode,
                region=region,
                role=role,
                map_filter=map_filter,
                competitive_division=competitive_division,
                order_by=order_by,
            )
        except ParserBlizzardError as exc:
            raise HTTPException(
                status_code=exc.status_code, detail=exc.message
            ) from exc

        await self._update_api_cache(
            cache_key,
            data,
            settings.hero_stats_cache_timeout,
            staleness_threshold=settings.hero_stats_staleness_threshold,
        )
        return data, False, 0


# ---------------------------------------------------------------------------
# Module-level helpers (kept accessible for tests)
# ---------------------------------------------------------------------------


def _merge_hero_data(
    hero_data: dict,
    heroes_list: list[dict],
    heroes_hitpoints: dict,
    hero_key: str,
) -> dict:
    """Merge data from hero details, heroes list, and heroes hitpoints."""
    try:
        portrait_value = next(
            hero["portrait"] for hero in heroes_list if hero["key"] == hero_key
        )
    except StopIteration:
        portrait_value = None
    else:
        hero_data = dict_insert_value_before_key(
            hero_data, "role", "portrait", portrait_value
        )

    try:
        hitpoints = heroes_hitpoints[hero_key]["hitpoints"]
    except KeyError:
        hitpoints = None
    else:
        hero_data = dict_insert_value_before_key(
            hero_data, "abilities", "hitpoints", hitpoints
        )

    return hero_data


def dict_insert_value_before_key(
    data: dict,
    key: str,
    new_key: str,
    new_value: Any,
) -> dict:
    """Insert ``new_key: new_value`` before ``key`` in ``data``."""
    if key not in data:
        raise KeyError
    pos = list(data.keys()).index(key)
    items = list(data.items())
    items.insert(pos, (new_key, new_value))
    return dict(items)
