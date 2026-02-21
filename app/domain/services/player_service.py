"""Player domain service — career, stats, summary, and search"""

import time
from typing import TYPE_CHECKING, cast

from fastapi import HTTPException, status

from app.adapters.blizzard.parsers.player_career_stats import (
    parse_player_career_stats_from_html,
)
from app.adapters.blizzard.parsers.player_profile import (
    extract_name_from_profile_html,
    fetch_player_html,
    filter_all_stats_data,
    filter_stats_by_query,
    parse_player_profile_html,
)
from app.adapters.blizzard.parsers.player_search import parse_player_search
from app.adapters.blizzard.parsers.player_stats import (
    parse_player_stats_summary_from_html,
)
from app.adapters.blizzard.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary_json,
)
from app.adapters.blizzard.parsers.utils import is_blizzard_id
from app.config import settings
from app.domain.services.base_service import BaseService
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error
from app.monitoring.metrics import (
    sqlite_battletag_lookup_total,
    sqlite_cache_hit_total,
    storage_hits_total,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.players.enums import (
        HeroKeyCareerFilter,
        PlayerGamemode,
        PlayerPlatform,
    )


class PlayerService(BaseService):
    """Domain service for all player-related endpoints.

    Wraps identity resolution, SQLite profile caching, and SWR staleness logic
    that was previously scattered across multiple controllers.
    """

    # ------------------------------------------------------------------
    # Search  (Valkey-only, no SQLite, no SWR)
    # ------------------------------------------------------------------

    async def search_players(
        self,
        name: str,
        order_by: str,
        offset: int,
        limit: int,
        cache_key: str,
    ) -> dict:
        """Search for players by name — Valkey-only cache, no persistent storage."""
        try:
            data = await parse_player_search(
                self.blizzard_client,
                name=name,
                order_by=order_by,
                offset=offset,
                limit=limit,
            )
        except ParserParsingError as exc:
            search_name = name.split("-", 1)[0]
            blizzard_url = (
                f"{settings.blizzard_host}{settings.search_account_path}/{search_name}/"
            )
            raise overfast_internal_error(blizzard_url, exc) from exc

        await self._update_api_cache(
            cache_key, data, settings.search_account_path_cache_timeout
        )
        return data

    # ------------------------------------------------------------------
    # Player summary  (GET /players/{player_id}/summary)
    # ------------------------------------------------------------------

    async def get_player_summary(
        self,
        player_id: str,
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return player summary (name, avatar, competitive ranks, …)."""

        def extract(html: str, player_summary: dict) -> dict:
            return parse_player_profile_html(html, player_summary).get("summary") or {}

        return await self._execute_player_request(player_id, cache_key, extract)

    # ------------------------------------------------------------------
    # Player career  (GET /players/{player_id})
    # ------------------------------------------------------------------

    async def get_player_career(
        self,
        player_id: str,
        gamemode: PlayerGamemode | None,
        platform: PlayerPlatform | None,
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return full player data: summary + stats."""

        def extract(html: str, player_summary: dict) -> dict:
            profile = parse_player_profile_html(html, player_summary)
            return {
                "summary": profile.get("summary") or {},
                "stats": filter_all_stats_data(
                    profile.get("stats") or {}, platform, gamemode
                ),
            }

        return await self._execute_player_request(player_id, cache_key, extract)

    # ------------------------------------------------------------------
    # Player stats  (GET /players/{player_id}/stats)
    # ------------------------------------------------------------------

    async def get_player_stats(
        self,
        player_id: str,
        gamemode: PlayerGamemode | None,
        platform: PlayerPlatform | None,
        hero: HeroKeyCareerFilter | None,  # ty: ignore[invalid-type-form]
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return player stats with category labels."""

        def extract(html: str, player_summary: dict) -> dict:
            profile = parse_player_profile_html(html, player_summary)
            return filter_stats_by_query(
                profile.get("stats") or {}, platform, gamemode, hero
            )

        return await self._execute_player_request(player_id, cache_key, extract)

    # ------------------------------------------------------------------
    # Player stats summary  (GET /players/{player_id}/stats/summary)
    # ------------------------------------------------------------------

    async def get_player_stats_summary(
        self,
        player_id: str,
        gamemode: PlayerGamemode | None,
        platform: PlayerPlatform | None,
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return player statistics summary (winrate, kda, …)."""

        def extract(html: str, player_summary: dict) -> dict:
            return parse_player_stats_summary_from_html(
                html, player_summary, gamemode, platform
            )

        return await self._execute_player_request(player_id, cache_key, extract)

    # ------------------------------------------------------------------
    # Player career stats  (GET /players/{player_id}/stats/career)
    # ------------------------------------------------------------------

    async def get_player_career_stats(
        self,
        player_id: str,
        gamemode: PlayerGamemode | None,
        platform: PlayerPlatform | None,
        hero: HeroKeyCareerFilter | None,  # ty: ignore[invalid-type-form]
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return player career stats (no labels)."""

        def extract(html: str, player_summary: dict) -> dict:
            return parse_player_career_stats_from_html(
                html, player_summary, platform, gamemode, hero
            )

        return await self._execute_player_request(player_id, cache_key, extract)

    # ------------------------------------------------------------------
    # Core request execution — universal scaffold
    # ------------------------------------------------------------------

    async def _execute_player_request(
        self,
        player_id: str,
        cache_key: str,
        data_factory: Callable[[str, dict], dict],
    ) -> tuple[dict, bool, int]:
        """Resolve identity → get HTML → compute data → update cache → return.

        Args:
            player_id: BattleTag or Blizzard ID.
            cache_key: Valkey API-cache key to write after serving.
            data_factory: Pure function ``(html, player_summary) → dict`` that
                          extracts the endpoint-specific payload from the raw HTML.
        """
        cache_key_player = player_id
        battletag_input: str | None = None
        player_summary: dict = {}
        data: dict = {}

        try:
            (
                blizzard_id,
                player_summary,
                cached_html,
                battletag_input,
            ) = await self._resolve_player_identity(player_id)
            cache_key_player = blizzard_id or player_id

            html = await self._get_player_html(
                cache_key_player, player_summary, cached_html, battletag_input
            )
            data = data_factory(html, player_summary)
        except Exception as exc:  # noqa: BLE001
            await self._handle_player_exceptions(
                exc, cache_key_player, battletag_input, player_summary
            )

        is_stale = self._check_player_staleness(cache_key_player)
        await self._update_api_cache(
            cache_key, data, settings.career_path_cache_timeout
        )
        return data, is_stale, 0

    # ------------------------------------------------------------------
    # Profile caching helpers
    # ------------------------------------------------------------------

    async def get_player_profile_cache(self, player_id: str) -> dict | None:
        """Get player profile from SQLite storage."""
        profile = await self.storage.get_player_profile(player_id)
        if not profile:
            if settings.prometheus_enabled:
                sqlite_cache_hit_total.labels(
                    table="player_profiles", result="miss"
                ).inc()
                storage_hits_total.labels(result="miss").inc()
            return None

        if settings.prometheus_enabled:
            sqlite_cache_hit_total.labels(table="player_profiles", result="hit").inc()
            storage_hits_total.labels(result="hit").inc()

        return {
            "profile": profile["html"],
            "summary": profile["summary"],
            "battletag": profile.get("battletag"),
            "name": profile.get("name"),
            "updated_at": profile.get("updated_at", 0),
        }

    async def update_player_profile_cache(
        self,
        player_id: str,
        player_summary: dict,
        html: str,
        battletag: str | None = None,
        name: str | None = None,
    ) -> None:
        """Store player profile in SQLite."""
        await self.storage.set_player_profile(
            player_id=player_id,
            html=html,
            summary=player_summary if player_summary else None,
            battletag=battletag,
            name=name,
        )

    def _check_player_staleness(self, _player_id: str) -> bool:
        """Return is_stale based purely on time — best effort.

        Phase 5 will perform an actual async storage lookup; for now always
        returns False (fresh) and lets the background refresh handle real staleness.
        """
        return False

    async def _get_player_html(
        self,
        blizzard_id: str,
        player_summary: dict,
        cached_html: str | None,
        battletag_input: str | None,
    ) -> str:
        """Return player HTML, always storing fresh HTML in SQLite.

        Priority order:
        1. ``cached_html`` — fetched during identity resolution; store and return.
        2. SQLite hit with matching ``lastUpdated`` — return cached HTML, backfilling
           battletag if it was missing.
        3. Fetch from Blizzard, store, return.
        """
        if cached_html:
            name = extract_name_from_profile_html(cached_html) or player_summary.get(
                "name"
            )
            await self.update_player_profile_cache(
                blizzard_id, player_summary, cached_html, battletag_input, name
            )
            return cached_html

        player_cache = await self.get_player_profile_cache(blizzard_id)
        if (
            player_cache is not None
            and player_summary
            and player_cache["summary"].get("lastUpdated")
            == player_summary.get("lastUpdated")
        ):
            html = cast("str", player_cache["profile"])
            if battletag_input and not player_cache.get("battletag"):
                await self.update_player_profile_cache(
                    blizzard_id,
                    player_summary,
                    html,
                    battletag_input,
                    player_cache.get("name"),
                )
            return html

        html, _ = await fetch_player_html(self.blizzard_client, blizzard_id)
        name = extract_name_from_profile_html(html) or player_summary.get("name")
        await self.update_player_profile_cache(
            blizzard_id, player_summary, html, battletag_input, name
        )
        return html

    # ------------------------------------------------------------------
    # Identity resolution
    # ------------------------------------------------------------------

    async def _resolve_player_identity(
        self, player_id: str
    ) -> tuple[str | None, dict, str | None, str | None]:
        """Resolve BattleTag or Blizzard ID to a canonical (blizzard_id, summary, html, battletag)."""
        logger.info("Retrieving Player Summary...")

        if is_blizzard_id(player_id):
            logger.info("Player ID is a Blizzard ID — attempting reverse enrichment")
            player_summary, html = await self._enrich_from_blizzard_id(player_id)
            return player_id, player_summary, html, None

        battletag_input = player_id
        search_json = await fetch_player_summary_json(self.blizzard_client, player_id)
        player_summary = parse_player_summary_json(search_json, player_id)

        if player_summary:
            logger.info("Player Summary retrieved!")
            blizzard_id = player_summary.get("url")
            return blizzard_id, player_summary, None, battletag_input

        logger.info(
            "Player not found in search — checking SQLite for cached Blizzard ID"
        )
        cached_blizzard_id = await self.storage.get_player_id_by_battletag(
            battletag_input
        )

        if cached_blizzard_id:
            if settings.prometheus_enabled:
                sqlite_battletag_lookup_total.labels(result="hit").inc()
            player_summary = parse_player_summary_json(
                search_json, player_id, cached_blizzard_id
            )
            if player_summary:
                return cached_blizzard_id, player_summary, None, battletag_input
        elif settings.prometheus_enabled:
            sqlite_battletag_lookup_total.labels(result="miss").inc()

        logger.info("No cached mapping — resolving via Blizzard redirect")
        html, blizzard_id = await fetch_player_html(self.blizzard_client, player_id)

        if blizzard_id and search_json:
            player_summary = parse_player_summary_json(
                search_json, player_id, blizzard_id
            )
            if player_summary:
                return blizzard_id, player_summary, html, battletag_input

        return blizzard_id, {}, html, battletag_input

    async def _enrich_from_blizzard_id(
        self, blizzard_id: str
    ) -> tuple[dict, str | None]:
        """Reverse-enrich: fetch HTML → extract name → search for summary."""
        html, _ = await fetch_player_html(self.blizzard_client, blizzard_id)
        if not html:
            return {}, None

        try:
            player_name = extract_name_from_profile_html(html)
            if player_name:
                search_json = await fetch_player_summary_json(
                    self.blizzard_client, player_name
                )
                player_summary = parse_player_summary_json(
                    search_json, player_name, blizzard_id
                )
                if player_summary:
                    return player_summary, html
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Reverse enrichment failed: {exc}")

        return {}, html

    # ------------------------------------------------------------------
    # Unknown player tracking
    # ------------------------------------------------------------------

    def _calculate_retry_after(self, check_count: int) -> int:
        base = settings.unknown_player_initial_retry
        multiplier = settings.unknown_player_retry_multiplier
        max_retry = settings.unknown_player_max_retry
        retry_after = base * (multiplier ** (check_count - 1))
        return min(int(retry_after), max_retry)

    async def _mark_player_unknown(
        self,
        blizzard_id: str,
        exception: HTTPException,
        battletag: str | None = None,
    ) -> None:
        if not settings.unknown_players_cache_enabled:
            return
        if exception.status_code != status.HTTP_404_NOT_FOUND:
            return

        player_status = await self.cache.get_player_status(blizzard_id)
        check_count = player_status["check_count"] + 1 if player_status else 1
        retry_after = self._calculate_retry_after(check_count)
        next_check_at = int(time.time()) + retry_after

        await self.cache.set_player_status(
            blizzard_id, check_count, retry_after, battletag=battletag
        )

        exception.detail = {
            "error": "Player not found",
            "retry_after": retry_after,
            "next_check_at": next_check_at,
            "check_count": check_count,
        }

        logger.info(
            f"Marked player {blizzard_id} as unknown (check #{check_count}, "
            f"retry in {retry_after}s)"
        )

    async def _handle_player_exceptions(
        self,
        error: Exception,
        cache_key: str,
        battletag_input: str | None,
        player_summary: dict,
    ) -> None:
        """Translate all player exceptions to HTTPException and always raise."""
        if isinstance(error, ParserBlizzardError):
            exc = HTTPException(status_code=error.status_code, detail=error.message)
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self._mark_player_unknown(
                    cache_key, exc, battletag=battletag_input
                )
            raise exc from error

        if isinstance(error, ParserParsingError):
            if "Could not find main content in HTML" in str(error):
                exc = HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Player not found",
                )
                await self._mark_player_unknown(
                    cache_key, exc, battletag=battletag_input
                )
                raise exc from error

            blizzard_url = (
                f"{settings.blizzard_host}{settings.career_path}/"
                f"{player_summary.get('url', cache_key) if player_summary else cache_key}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error

        if isinstance(error, HTTPException):
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self._mark_player_unknown(
                    cache_key, error, battletag=battletag_input
                )
            raise error

        raise error
