"""Player Career Controller module"""

from typing import TYPE_CHECKING, ClassVar, cast

from fastapi import HTTPException, status

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_profile import (
    extract_name_from_profile_html,
    fetch_player_html,
    filter_all_stats_data,
    filter_stats_by_query,
    parse_player_profile_html,
)
from app.config import settings
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort
    from app.players.enums import PlayerGamemode, PlayerPlatform

from .base_player_controller import BasePlayerController, with_unknown_player_guard


class GetPlayerCareerController(BasePlayerController):
    """Player Career Controller used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc.
    """

    parser_classes: ClassVar[list] = []
    timeout = settings.career_path_cache_timeout

    @with_unknown_player_guard
    async def process_request(self, **kwargs) -> dict:
        """Process request with Player Cache support and unknown player guard"""
        player_id = kwargs["player_id"]
        client = BlizzardClient()

        # Initialize variables for exception handling
        cache_key = player_id
        battletag_input = None

        try:
            # Step 1: Resolve player identity (search + Blizzard ID resolution)
            # Phase 3.5B: Returns (blizzard_id, summary, cached_html, battletag_input)
            (
                blizzard_id,
                player_summary,
                cached_html,
                battletag_input,
            ) = await self._resolve_player_identity(client, player_id)

            # Use Blizzard ID as canonical key (fallback to player_id if not resolved yet)
            cache_key = blizzard_id or player_id

            # Step 2: Fetch profile with cache optimization
            # Pass cached_html to avoid redundant Blizzard call
            _html, profile_data = await self._fetch_profile_with_cache(
                client,
                cache_key,
                player_summary,
                battletag_input,
                cached_html=cached_html,
            )

            # Step 3: Apply filters
            data = self._filter_profile_data(
                profile_data,
                bool(kwargs.get("summary")),
                bool(kwargs.get("stats")),
                kwargs.get("platform"),
                kwargs.get("gamemode"),
                kwargs.get("hero"),
            )

        except ParserBlizzardError as error:
            exception = HTTPException(
                status_code=error.status_code,
                detail=error.message,
            )
            # Mark unknown on 404 from Blizzard
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self.mark_player_unknown_on_404(
                    cache_key, exception, battletag=battletag_input
                )
            raise exception from error
        except ParserParsingError as error:
            # Check if error message indicates player not found
            # This can happen when HTML structure is malformed or missing expected elements
            if "Could not find main content in HTML" in str(error):
                exception = HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Player not found",
                )
                # Mark unknown with Blizzard ID (primary) and BattleTag (if available)
                await self.mark_player_unknown_on_404(
                    cache_key, exception, battletag=battletag_input
                )
                raise exception from error

            # Get Blizzard URL for error reporting
            blizzard_url = (
                f"{settings.blizzard_host}{settings.career_path}/"
                f"{player_summary.get('url', cache_key) if player_summary else cache_key}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error
        except HTTPException as exception:
            # Mark unknown on any 404 (explicit HTTPException)
            if exception.status_code == status.HTTP_404_NOT_FOUND:
                await self.mark_player_unknown_on_404(
                    cache_key, exception, battletag=battletag_input
                )
            raise

        # Update API Cache
        await self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data

    async def _fetch_profile_with_cache(
        self,
        client: BlizzardClientPort,
        blizzard_id: str,
        player_summary: dict,
        battletag_input: str | None,
        cached_html: str | None = None,
    ) -> tuple[str, dict]:
        """Fetch player profile HTML with cache optimization.

        Phase 3.5B: Uses Blizzard ID as cache key, extracts name from HTML,
        stores battletag as optional metadata.

        Args:
            client: Blizzard API client
            blizzard_id: Blizzard ID (canonical cache key)
            player_summary: Player summary from search (may be empty for direct Blizzard ID requests)
            battletag_input: BattleTag from user input (None if user provided Blizzard ID)
            cached_html: HTML already fetched during identity resolution (Step 1 optimization)

        Returns:
            Tuple of (html, profile_data)
        """
        # Step 1 optimization: Use cached HTML from _resolve_player_identity
        if cached_html:
            logger.info(
                "Using cached HTML from identity resolution (avoiding double-fetch)"
            )
            profile_data = parse_player_profile_html(cached_html, player_summary)

            # Extract name and store profile
            name = extract_name_from_profile_html(cached_html) or player_summary.get(
                "name"
            )
            await self.update_player_profile_cache(
                blizzard_id, player_summary, cached_html, battletag_input, name
            )

            return cached_html, profile_data

        # Check Player Cache (SQLite storage) using Blizzard ID as key
        logger.info("Checking Player Cache...")
        player_cache = await self.get_player_profile_cache(blizzard_id)

        if (
            player_cache is not None
            and player_summary  # Have summary to compare
            and player_cache["summary"]["lastUpdated"]  # ty: ignore[invalid-argument-type, not-subscriptable]
            == player_summary["lastUpdated"]
        ):
            logger.info("Player Cache found and up-to-date, using it")
            html = cast("str", player_cache["profile"])
            profile_data = parse_player_profile_html(html, player_summary)

            # Update battletag if provided (progressive enhancement)
            if battletag_input and not player_cache.get("battletag"):
                logger.info(f"Enriching cache with BattleTag: {battletag_input}")
                cached_name = player_cache.get("name")
                name_str = cached_name if isinstance(cached_name, str) else None
                await self.update_player_profile_cache(
                    blizzard_id, player_summary, html, battletag_input, name_str
                )

            return html, profile_data

        # Fetch from Blizzard with Blizzard ID
        logger.info("Player Cache not found or not up-to-date, calling Blizzard")
        html, _ = await fetch_player_html(client, blizzard_id)
        profile_data = parse_player_profile_html(html, player_summary)

        # Extract name and Update Player Cache (SQLite storage)
        name = extract_name_from_profile_html(html) or player_summary.get("name")
        await self.update_player_profile_cache(
            blizzard_id, player_summary, html, battletag_input, name
        )

        return html, profile_data

    async def _fetch_player_html(
        self, client: BlizzardClientPort, player_id: str
    ) -> tuple[str, str | None]:
        """Fetch player HTML from Blizzard and extract Blizzard ID from redirect"""
        return await fetch_player_html(client, player_id)

    def _filter_profile_data(
        self,
        profile_data: dict,
        summary_filter: bool,
        stats_filter: bool,
        platform_filter: PlayerPlatform | None,
        gamemode_filter: PlayerGamemode | None,
        hero_filter: str | None,
    ) -> dict:
        """Apply query filters to profile data"""
        # If only summary requested
        if summary_filter:
            return profile_data.get("summary") or {}

        # If only stats requested
        if stats_filter:
            return filter_stats_by_query(
                profile_data.get("stats") or {},
                platform_filter,
                gamemode_filter,
                hero_filter,
            )

        # Both summary and stats (with optional platform/gamemode filters)
        return {
            "summary": profile_data.get("summary") or {},
            "stats": filter_all_stats_data(
                profile_data.get("stats") or {},
                platform_filter,
                gamemode_filter,
            ),
        }
