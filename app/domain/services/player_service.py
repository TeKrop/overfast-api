"""Player domain service — career, stats, summary, and search"""

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Never, cast

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
    storage_battletag_lookup_total,
    storage_cache_hit_total,
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


@dataclass
class PlayerIdentity:
    """Result of player identity resolution.

    Groups the four fields that travel together after resolving a
    BattleTag or Blizzard ID to a canonical identity.
    """

    blizzard_id: str | None = field(default=None)
    player_summary: dict = field(default_factory=dict)
    cached_html: str | None = field(default=None)
    battletag_input: str | None = field(default=None)


@dataclass
class PlayerRequest:
    """Parameter object for a player data request.

    Pass a single ``PlayerRequest`` to ``PlayerService._execute_player_request``
    instead of passing each field as a separate keyword argument.
    """

    player_id: str
    cache_key: str
    data_factory: Callable[[str, dict], dict]


class PlayerService(BaseService):
    """Domain service for all player-related endpoints.

    Wraps identity resolution, persistent storage profile caching, and SWR staleness logic
    that was previously scattered across multiple controllers.
    """

    # ------------------------------------------------------------------
    # Search  (Valkey-only, no persistent storage, no SWR)
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

        return await self._execute_player_request(
            PlayerRequest(
                player_id=player_id, cache_key=cache_key, data_factory=extract
            )
        )

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

        return await self._execute_player_request(
            PlayerRequest(
                player_id=player_id, cache_key=cache_key, data_factory=extract
            )
        )

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

        return await self._execute_player_request(
            PlayerRequest(
                player_id=player_id, cache_key=cache_key, data_factory=extract
            )
        )

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

        return await self._execute_player_request(
            PlayerRequest(
                player_id=player_id, cache_key=cache_key, data_factory=extract
            )
        )

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

        return await self._execute_player_request(
            PlayerRequest(
                player_id=player_id, cache_key=cache_key, data_factory=extract
            )
        )

    # ------------------------------------------------------------------
    # Core request execution — universal scaffold
    # ------------------------------------------------------------------

    async def _execute_player_request(
        self, request: PlayerRequest
    ) -> tuple[dict, bool, int]:
        """Resolve identity → get HTML → compute data → update cache → return.

        Fast path: if persistent storage has a profile fresher than
        ``player_staleness_threshold``, all Blizzard calls are skipped and
        the cached HTML + summary are used directly.

        Args:
            request: ``PlayerRequest`` holding ``player_id``, ``cache_key``,
                     and the endpoint-specific ``data_factory``.
        """
        identity = PlayerIdentity()
        effective_id = request.player_id
        data: dict = {}
        age = 0

        try:
            fresh = await self._get_fresh_stored_profile(request.player_id)
            if fresh is not None:
                profile, age = fresh
                logger.info(
                    "Serving player data from persistent storage (within staleness threshold)"
                )
                data = request.data_factory(profile["profile"], profile["summary"])
            else:
                identity = await self._resolve_player_identity(request.player_id)
                effective_id = identity.blizzard_id or request.player_id
                html = await self._get_player_html(effective_id, identity)
                data = request.data_factory(html, identity.player_summary)
        except Exception as exc:  # noqa: BLE001
            await self._handle_player_exceptions(exc, request.player_id, identity)

        is_stale = self._check_player_staleness()
        await self._update_api_cache(
            request.cache_key, data, settings.career_path_cache_timeout
        )
        return data, is_stale, age

    # ------------------------------------------------------------------
    # Profile caching helpers
    # ------------------------------------------------------------------

    async def get_player_profile_cache(self, player_id: str) -> dict | None:
        """Get player profile from persistent storage."""
        profile = await self.storage.get_player_profile(player_id)
        if not profile:
            if settings.prometheus_enabled:
                storage_cache_hit_total.labels(
                    table="player_profiles", result="miss"
                ).inc()
                storage_hits_total.labels(result="miss").inc()
            return None

        if settings.prometheus_enabled:
            storage_cache_hit_total.labels(table="player_profiles", result="hit").inc()
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
        """Store player profile in persistent storage."""
        await self.storage.set_player_profile(
            player_id=player_id,
            html=html,
            summary=player_summary or None,
            battletag=battletag,
            name=name,
        )

    def _check_player_staleness(self) -> bool:
        """Return is_stale — stub always returning False until Phase 5.

        Phase 5 will perform a real async storage lookup comparing
        ``player_profiles.updated_at`` against ``player_staleness_threshold``.
        """
        return False

    async def _get_fresh_stored_profile(
        self, player_id: str
    ) -> tuple[dict, int] | None:
        """Return ``(profile, age_seconds)`` if the stored profile was updated within
        ``player_staleness_threshold``, else ``None``.

        For BattleTag inputs, resolves to a Blizzard ID via the stored mapping
        before fetching the profile.  Returns ``None`` if no mapping exists, the
        profile is absent, or the profile is older than the threshold.
        """
        if is_blizzard_id(player_id):
            blizzard_id = player_id
        else:
            blizzard_id = await self.storage.get_player_id_by_battletag(player_id)
            if not blizzard_id:
                return None

        profile = await self.get_player_profile_cache(blizzard_id)
        if not profile:
            return None

        age = int(time.time()) - profile["updated_at"]
        if age < settings.player_staleness_threshold:
            logger.info(
                "Stored profile for {} is {:.0f}s old (threshold {}s) — skipping Blizzard",
                player_id,
                age,
                settings.player_staleness_threshold,
            )
            return profile, age

        return None

    async def _get_player_html(
        self,
        effective_id: str,
        identity: PlayerIdentity,
    ) -> str:
        """Return player HTML, always storing fresh HTML in persistent storage.

        Priority order:
        1. ``identity.cached_html`` — fetched during identity resolution; store and return.
        2. persistent storage hit with matching ``lastUpdated`` — return cached HTML, backfilling
           battletag if it was missing.
        3. Fetch from Blizzard, store, return.
        """
        if identity.cached_html:
            name = extract_name_from_profile_html(
                identity.cached_html
            ) or identity.player_summary.get("name")
            await self.update_player_profile_cache(
                effective_id,
                identity.player_summary,
                identity.cached_html,
                identity.battletag_input,
                name,
            )
            return identity.cached_html

        player_cache = await self.get_player_profile_cache(effective_id)
        if (
            player_cache is not None
            and identity.player_summary
            and player_cache["summary"].get("lastUpdated")
            == identity.player_summary.get("lastUpdated")
        ):
            html = cast("str", player_cache["profile"])
            if identity.battletag_input and not player_cache.get("battletag"):
                await self.update_player_profile_cache(
                    effective_id,
                    identity.player_summary,
                    html,
                    identity.battletag_input,
                    player_cache.get("name"),
                )
            return html

        html, _ = await fetch_player_html(self.blizzard_client, effective_id)
        name = extract_name_from_profile_html(html) or identity.player_summary.get(
            "name"
        )
        await self.update_player_profile_cache(
            effective_id,
            identity.player_summary,
            html,
            identity.battletag_input,
            name,
        )
        return html

    # ------------------------------------------------------------------
    # Identity resolution
    # ------------------------------------------------------------------

    async def _resolve_player_identity(self, player_id: str) -> PlayerIdentity:
        """Resolve BattleTag or Blizzard ID to a canonical ``PlayerIdentity``."""
        logger.info("Retrieving Player Summary...")
        if is_blizzard_id(player_id):
            return await self._resolve_blizzard_id_identity(player_id)
        return await self._resolve_battletag_identity(player_id)

    async def _resolve_blizzard_id_identity(self, player_id: str) -> PlayerIdentity:
        """Resolve a raw Blizzard ID via reverse enrichment."""
        logger.info("Player ID is a Blizzard ID — attempting reverse enrichment")
        player_summary, html = await self._enrich_from_blizzard_id(player_id)
        return PlayerIdentity(
            blizzard_id=player_id,
            player_summary=player_summary,
            cached_html=html,
        )

    async def _resolve_battletag_identity(self, player_id: str) -> PlayerIdentity:
        """Resolve a BattleTag to a ``PlayerIdentity`` using search + fallbacks."""
        battletag_input = player_id
        search_json = await fetch_player_summary_json(self.blizzard_client, player_id)
        player_summary = parse_player_summary_json(search_json, player_id)

        if player_summary:
            logger.info("Player Summary retrieved!")
            return PlayerIdentity(
                blizzard_id=player_summary.get("url"),
                player_summary=player_summary,
                battletag_input=battletag_input,
            )

        if search_json:
            identity = await self._try_cached_blizzard_id(
                battletag_input, player_id, search_json
            )
            if identity:
                return identity

        return await self._resolve_via_redirect(player_id, battletag_input, search_json)

    async def _try_cached_blizzard_id(
        self, battletag_input: str, player_id: str, search_json: list
    ) -> PlayerIdentity | None:
        """Check storage for a cached Blizzard ID and retry the search with it."""
        logger.info(
            "Player not found in search — checking persistent storage for cached Blizzard ID"
        )
        cached_blizzard_id = await self.storage.get_player_id_by_battletag(
            battletag_input
        )

        if not cached_blizzard_id:
            if settings.prometheus_enabled:
                storage_battletag_lookup_total.labels(result="miss").inc()
            return None

        logger.info("Blizzard ID found — retrying to find in search")
        if settings.prometheus_enabled:
            storage_battletag_lookup_total.labels(result="hit").inc()
        player_summary = parse_player_summary_json(
            search_json, player_id, cached_blizzard_id
        )
        if player_summary:
            return PlayerIdentity(
                blizzard_id=cached_blizzard_id,
                player_summary=player_summary,
                battletag_input=battletag_input,
            )
        return None

    async def _resolve_via_redirect(
        self, player_id: str, battletag_input: str, search_json: list
    ) -> PlayerIdentity:
        """Resolve identity as a last resort via Blizzard redirect HTML fetch."""
        logger.info("No cached mapping — resolving via Blizzard redirect")
        html, blizzard_id = await fetch_player_html(self.blizzard_client, player_id)

        if blizzard_id and search_json:
            player_summary = parse_player_summary_json(
                search_json, player_id, blizzard_id
            )
            if player_summary:
                return PlayerIdentity(
                    blizzard_id=blizzard_id,
                    player_summary=player_summary,
                    cached_html=html,
                    battletag_input=battletag_input,
                )

        return PlayerIdentity(
            blizzard_id=blizzard_id,
            cached_html=html,
            battletag_input=battletag_input,
        )

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
        player_id: str,
        identity: PlayerIdentity,
    ) -> Never:
        """Translate all player exceptions to HTTPException and always raise."""
        effective_id = identity.blizzard_id or player_id
        battletag_input = identity.battletag_input
        player_summary = identity.player_summary

        if isinstance(error, ParserBlizzardError):
            exc = HTTPException(status_code=error.status_code, detail=error.message)
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self._mark_player_unknown(
                    effective_id, exc, battletag=battletag_input
                )
            raise exc from error

        if isinstance(error, ParserParsingError):
            if "Could not find main content in HTML" in str(error):
                exc = HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Player not found",
                )
                await self._mark_player_unknown(
                    effective_id, exc, battletag=battletag_input
                )
                raise exc from error

            blizzard_url = (
                f"{settings.blizzard_host}{settings.career_path}/"
                f"{player_summary.get('url', effective_id) if player_summary else effective_id}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error

        if isinstance(error, HTTPException):
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self._mark_player_unknown(
                    effective_id, error, battletag=battletag_input
                )
            raise error

        raise error
