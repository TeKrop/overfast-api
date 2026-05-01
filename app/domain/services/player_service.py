"""Player domain service — career, stats, summary, and search"""

import time
from http import HTTPStatus
from typing import Never, cast

from fastapi import HTTPException

from app.config import settings
from app.domain.enums import HeroKeyCareerFilter, PlayerGamemode, PlayerPlatform
from app.domain.exceptions import (
    ParserBlizzardError,
    ParserInternalError,
    ParserParsingError,
)
from app.domain.models.player import PlayerIdentity, PlayerRequest
from app.domain.parsers.player_career_stats import (
    parse_player_career_stats_from_html,
)
from app.domain.parsers.player_profile import (
    extract_name_from_profile_html,
    fetch_player_html,
    filter_all_stats_data,
    filter_stats_by_query,
    parse_player_profile_html,
)
from app.domain.parsers.player_search import parse_player_search
from app.domain.parsers.player_stats import (
    parse_player_stats_summary_from_html,
)
from app.domain.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary_json,
)
from app.domain.parsers.utils import is_blizzard_id
from app.domain.services.base_service import BaseService
from app.infrastructure.logger import logger
from app.monitoring.metrics import (
    storage_battletag_lookup_total,
    storage_cache_hit_total,
    storage_hits_total,
)


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
            raise ParserInternalError(blizzard_url, exc) from exc

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
    # Background refresh  (worker only — bypasses storage fast-path)
    # ------------------------------------------------------------------

    async def refresh_player_profile(self, player_id: str) -> None:
        """Unconditionally fetch fresh player data from Blizzard and persist it.

        Unlike the public endpoint methods, this method bypasses
        ``_get_fresh_stored_profile`` entirely, so the worker always
        issues a live Blizzard request regardless of how recently the
        profile was last stored.  This prevents the background refresh
        task from silently no-oping when the stored profile is still
        within the staleness threshold.

        After updating persistent storage, all existing API cache keys for this
        player are deleted.  The next request will find a cache miss, hit the
        storage fast-path (profile is now fresh), compute the correct data slice,
        and repopulate the cache — without touching Blizzard.
        """
        identity = PlayerIdentity()
        try:
            identity = await self._resolve_player_identity(player_id)
            effective_id = identity.blizzard_id or player_id
            await self._get_player_html(effective_id, identity, force_update=True)
            await self._evict_player_cache_keys(player_id)
        except Exception as exc:  # noqa: BLE001
            await self._handle_player_exceptions(exc, player_id, identity)

    async def _evict_player_cache_keys(self, player_id: str) -> None:
        """Delete all API cache keys for *player_id* from Valkey.

        Uses a glob scan so every endpoint/parameter combination is cleared
        without needing to enumerate them explicitly.  The next request for
        each key will hit the storage fast-path and repopulate the cache.
        """
        pattern = f"{settings.api_cache_key_prefix}:/players/{player_id}*"
        keys = await self.cache.scan_keys(pattern)
        for key in keys:
            await self.cache.delete(key)
        if keys:
            logger.debug(
                "[refresh] Evicted {} cache key(s) for {}", len(keys), player_id
            )

    # ------------------------------------------------------------------
    # Player stats  (GET /players/{player_id}/stats)
    # ------------------------------------------------------------------

    async def get_player_stats(
        self,
        player_id: str,
        gamemode: PlayerGamemode,
        platform: PlayerPlatform | None,
        hero: HeroKeyCareerFilter | None,
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return player stats with category labels."""

        def extract(html: str, player_summary: dict) -> dict:
            profile = parse_player_profile_html(html, player_summary)
            return filter_stats_by_query(
                profile.get("stats") or {}, gamemode, platform, hero
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
        gamemode: PlayerGamemode,
        platform: PlayerPlatform | None,
        hero: HeroKeyCareerFilter | None,
        cache_key: str,
    ) -> tuple[dict, bool, int]:
        """Return player career stats (no labels)."""

        def extract(html: str, player_summary: dict) -> dict:
            return parse_player_career_stats_from_html(
                html, gamemode, player_summary, platform, hero
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
        age: int = 0
        stored_at: int | None = None

        try:
            profile, age = await self._get_fresh_stored_profile(request.player_id)

            if profile is not None:
                stored_at = profile["updated_at"]
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

        is_stale = self._check_player_staleness(age)
        await self._update_api_cache(
            request.cache_key,
            data,
            settings.career_path_cache_timeout,
            stored_at=stored_at,
            staleness_threshold=settings.player_staleness_threshold,
            stale_while_revalidate=settings.stale_cache_timeout if is_stale else 0,
        )
        if is_stale:
            await self._enqueue_refresh("player_profile", request.player_id)
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

    def _check_player_staleness(self, age: int) -> bool:
        """Return True when the stored profile is old enough to warrant a background pre-refresh.

        Applies SWR semantics: if the profile was served from persistent storage
        (``age > 0``) and has consumed at least half its staleness window, the response
        is marked stale so the caller enqueues a background refresh.  This keeps profiles
        pre-warmed and avoids a synchronous Blizzard call on the next request.

        ``age == 0`` means we just fetched fresh data from Blizzard — never stale.

        The SWR lifecycle for a player profile across the two threshold values:

        - ``0 ≤ age < threshold // 2``  — fresh; served from storage, no refresh enqueued.
        - ``threshold // 2 ≤ age < threshold``  — stale window: served from storage *and*
          a background refresh is enqueued so the next request finds a warm profile.
        - ``age ≥ threshold``  — ``_get_fresh_stored_profile`` returns ``None``; the
          request falls through to a synchronous Blizzard fetch.
        """
        if age == 0:
            return False
        swr_threshold = settings.player_staleness_threshold // 2
        return age >= swr_threshold

    async def _get_fresh_stored_profile(
        self, player_id: str
    ) -> tuple[dict | None, int]:
        """Return ``(profile, age_seconds)`` if the stored profile was updated within
        ``player_staleness_threshold``, else ``(None, 0)``.

        For BattleTag inputs, resolves to a Blizzard ID via the stored mapping
        before fetching the profile.  Returns ``None`` if no mapping exists or if the
        profile is absent. Returns tuple with ``(None, age)`` if the profile exists
        but is older than the threshold.

        See ``_check_player_staleness`` for the full SWR lifecycle description.
        """
        if is_blizzard_id(player_id):
            blizzard_id = player_id
        else:
            blizzard_id = await self.storage.get_player_id_by_battletag(player_id)
            if not blizzard_id:
                return None, 0

        profile = await self.get_player_profile_cache(blizzard_id)
        if not profile:
            return None, 0

        age = int(time.time()) - profile["updated_at"]
        if age < settings.player_staleness_threshold:
            logger.info(
                "Stored profile for {} is {:.0f}s old (threshold {}s) — skipping Blizzard",
                player_id,
                age,
                settings.player_staleness_threshold,
            )
            return profile, age

        return None, age

    async def _get_player_html(
        self,
        effective_id: str,
        identity: PlayerIdentity,
        *,
        force_update: bool = False,
    ) -> str:
        """Return player HTML, always storing fresh HTML in persistent storage.

        Priority order:
        1. ``identity.cached_html`` — fetched during identity resolution; store and return.
        2. persistent storage hit with matching ``lastUpdated`` — the profile hasn't changed
           on Blizzard's side, so there is no need to re-fetch the HTML page.  When
           ``force_update=True`` (background worker), ``update_player_profile_cache`` is
           called with the existing HTML to bump ``updated_at`` and reset the staleness clock.
           Battletag is backfilled in either case when it was previously missing.
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
            if force_update or (
                identity.battletag_input and not player_cache.get("battletag")
            ):
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
                logger.debug("Player name {} found, fetching summary...", player_name)
                search_json = await fetch_player_summary_json(
                    self.blizzard_client, player_name
                )
                player_summary = parse_player_summary_json(
                    search_json, player_name, blizzard_id
                )
                if player_summary:
                    return player_summary, html
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reverse enrichment failed: {}", exc)

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
        if exception.status_code != HTTPStatus.NOT_FOUND.value:
            return

        player_status = await self.cache.get_player_status(blizzard_id)
        check_count = player_status["check_count"] + 1 if player_status else 1
        retry_after = self._calculate_retry_after(check_count)
        next_check_at = int(time.time()) + retry_after

        await self.cache.set_player_status(
            blizzard_id, check_count, retry_after, battletag=battletag
        )

        exception.detail = {  # ty: ignore[invalid-assignment]
            "error": "Player not found",
            "retry_after": retry_after,
            "next_check_at": next_check_at,
            "check_count": check_count,
        }

        logger.info(
            "Marked player {} as unknown (check #{}, retry in {}s)",
            blizzard_id,
            check_count,
            retry_after,
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
            if error.status_code == HTTPStatus.NOT_FOUND.value:
                await self._mark_player_unknown(
                    effective_id, exc, battletag=battletag_input
                )
            raise exc from error

        if isinstance(error, ParserParsingError):
            if "Could not find main content in HTML" in str(error):
                exc = HTTPException(
                    status_code=HTTPStatus.NOT_FOUND.value,
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
            raise ParserInternalError(blizzard_url, error) from error

        if isinstance(error, HTTPException):
            if error.status_code == HTTPStatus.NOT_FOUND.value:
                await self._mark_player_unknown(
                    effective_id, error, battletag=battletag_input
                )
            raise error

        raise error
