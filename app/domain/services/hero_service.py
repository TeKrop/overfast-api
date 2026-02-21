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
from app.adapters.blizzard.parsers.heroes_stats import parse_heroes_stats
from app.config import settings
from app.domain.services.base_service import BaseService
from app.enums import Locale
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error
from app.overfast_logger import logger

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


class HeroService(BaseService):
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
    ) -> tuple[list[dict], bool]:
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
            storage_key=f"heroes:{locale}",
            fetcher=_fetch,
            filter=_filter,
            cache_key=cache_key,
            cache_ttl=settings.heroes_path_cache_timeout,
            staleness_threshold=settings.heroes_staleness_threshold,
            entity_type="heroes",
        )

    # ------------------------------------------------------------------
    # Single hero  (GET /heroes/{hero_key})
    # ------------------------------------------------------------------

    async def get_hero(
        self,
        hero_key: str,
        locale: Locale,
        cache_key: str,
    ) -> tuple[dict, bool]:
        """Return full hero details merged with portrait and hitpoints.

        Single-hero data is not stored persistently; the Valkey API cache is
        still updated on every fetch.
        """
        try:
            hero_data = await parse_hero(self.blizzard_client, hero_key, locale)
            heroes_html = await fetch_heroes_html(self.blizzard_client, locale)
            heroes_list = parse_heroes_html(heroes_html)
            heroes_stats = parse_heroes_stats()
            data = _merge_hero_data(hero_data, heroes_list, heroes_stats, hero_key)
        except ParserBlizzardError as exc:
            raise HTTPException(
                status_code=exc.status_code, detail=exc.message
            ) from exc
        except ParserParsingError as exc:
            blizzard_url = (
                f"{settings.blizzard_host}/{locale}{settings.heroes_path}{hero_key}/"
            )
            raise overfast_internal_error(blizzard_url, exc) from exc

        await self._update_api_cache(cache_key, data, settings.hero_path_cache_timeout)
        return data, False

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
    ) -> tuple[list[dict], bool]:
        """Return hero usage statistics with SWR."""
        storage_key = _build_hero_stats_storage_key(
            platform, gamemode, region, map_filter, competitive_division
        )

        async def _fetch() -> list[dict]:
            try:
                return await parse_hero_stats_summary(
                    self.blizzard_client,  # ty: ignore[invalid-argument-type]
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

        def _filter(data: list[dict]) -> list[dict]:
            return _filter_hero_stats(data, role, order_by)

        return await self.get_or_fetch(
            storage_key=storage_key,
            fetcher=_fetch,
            filter=_filter,
            cache_key=cache_key,
            cache_ttl=settings.hero_stats_cache_timeout,
            staleness_threshold=settings.hero_stats_staleness_threshold,
            entity_type="hero_stats",
        )


# ---------------------------------------------------------------------------
# Module-level helpers (kept accessible for tests)
# ---------------------------------------------------------------------------


def _merge_hero_data(
    hero_data: dict,
    heroes_list: list[dict],
    heroes_stats: dict,
    hero_key: str,
) -> dict:
    """Merge data from hero details, heroes list, and heroes stats."""
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
        hitpoints = heroes_stats[hero_key]["hitpoints"]
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


def _build_hero_stats_storage_key(
    platform: Any,
    gamemode: Any,
    region: Any,
    map_filter: Any,
    competitive_division: Any,
) -> str:
    map_val = map_filter.value if map_filter else "all-maps"
    tier_val = competitive_division.value if competitive_division else "null"
    return (
        f"hero_stats:{platform.value}:{gamemode.value}:{region.value}"
        f":{map_val}:{tier_val}"
    )


def _filter_hero_stats(
    data: list[dict],
    role: Any,
    order_by: str,
) -> list[dict]:
    """Re-apply role filter and ordering (used both on stale data and cold-start)."""
    logger.debug("[SWR] Applying hero_stats filters")
    if role:
        data = [h for h in data if h.get("role") == role.value]
    field, direction = order_by.split(":")
    return sorted(data, key=lambda h: h.get(field, ""), reverse=(direction == "desc"))
