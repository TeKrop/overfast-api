"""Player Stats Summary Controller module"""

from typing import TYPE_CHECKING, ClassVar, cast

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_profile import (
    extract_name_from_profile_html,
    fetch_player_html,
)
from app.adapters.blizzard.parsers.player_stats import (
    parse_player_stats_summary_from_html,
)
from app.config import settings
from app.exceptions import ParserParsingError
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort
    from app.players.enums import PlayerGamemode, PlayerPlatform

from .base_player_controller import BasePlayerController, with_unknown_player_guard


class GetPlayerStatsSummaryController(BasePlayerController):
    """Player Stats Summary Controller used in order to retrieve essential
    stats of a player, often used for tracking progress: winrate, kda, damage, etc.
    """

    parser_classes: ClassVar[list] = []
    timeout = settings.career_path_cache_timeout

    @with_unknown_player_guard
    async def process_request(self, **kwargs) -> dict:
        """Process request with Player Cache support and unknown player guard"""
        player_id = kwargs["player_id"]
        gamemode = kwargs.get("gamemode")
        platform = kwargs.get("platform")
        client = BlizzardClient()

        # Initialize variables for exception handling (must be in scope for except block)
        cache_key = player_id
        battletag_input = None
        player_summary = {}

        try:
            # Step 1: Resolve player identity (search + Blizzard ID resolution)
            # Returns 4-tuple: (blizzard_id, summary, html, battletag_input)
            (
                blizzard_id,
                player_summary,
                cached_html,
                battletag_input,
            ) = await self._resolve_player_identity(client, player_id)

            # Use Blizzard ID as cache key (canonical identifier)
            cache_key = blizzard_id or player_id

            # Step 2: Fetch stats with cache optimization
            # Pass cached_html to avoid redundant Blizzard call
            data = await self._fetch_stats_with_cache(
                client,
                cache_key,
                player_summary,
                gamemode,
                platform,
                battletag_input=battletag_input,
                cached_html=cached_html,
            )

        except Exception as error:  # noqa: BLE001
            # Use shared exception handler (always raises)
            await self.handle_player_request_exceptions(
                error, cache_key, battletag_input, player_summary
            )

        # Update API Cache
        await self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data

    async def _fetch_stats_with_cache(
        self,
        client: BlizzardClientPort,
        blizzard_id: str | None,
        player_summary: dict,
        gamemode: PlayerGamemode | None,
        platform: PlayerPlatform | None,
        battletag_input: str | None = None,
        cached_html: str | None = None,
    ) -> dict:
        """Fetch player stats with cache optimization.

        Uses Blizzard ID as the canonical identifier for all caching operations.
        BattleTag is stored as optional metadata but never used as a cache key.

        Args:
            client: Blizzard API client
            blizzard_id: Player's Blizzard ID (canonical identifier)
            player_summary: Player summary from search
            gamemode: Optional gamemode filter
            platform: Optional platform filter
            battletag_input: BattleTag from user's request URL (optional metadata)
            cached_html: HTML already fetched during identity resolution

        Returns:
            Player stats summary data
        """
        # Step 1 optimization: Use cached HTML from _resolve_player_identity
        if cached_html:
            logger.info(
                "Using cached HTML from identity resolution (avoiding double-fetch)"
            )
            return parse_player_stats_summary_from_html(
                cached_html, player_summary, gamemode, platform
            )

        # No Blizzard ID - should not happen but handle defensively
        if not blizzard_id:
            msg = "Unable to resolve player identity"
            logger.warning("No Blizzard ID available, cannot fetch stats")
            raise ParserParsingError(msg)

        # Check Player Cache (SQLite storage) - keyed by Blizzard ID
        logger.info(f"Checking Player Cache for Blizzard ID: {blizzard_id}")
        player_cache = await self.get_player_profile_cache(blizzard_id)

        if player_cache is not None:
            cached_summary = player_cache["summary"]  # ty: ignore[invalid-argument-type]

            # Case 1: Have fresh summary to compare — validate cache freshness
            if (
                player_summary
                and cached_summary["lastUpdated"]  # ty: ignore[not-subscriptable]
                == player_summary["lastUpdated"]
            ):
                logger.info("Player Cache found and up-to-date, using it")
                html = cast("str", player_cache["profile"])
                return parse_player_stats_summary_from_html(
                    html, player_summary, gamemode, platform
                )

            # Case 2: No summary available (e.g. Blizzard rate-limited) — use
            # cached data as fallback so we can still serve a response instead
            # of hitting Blizzard again (which would also fail).
            if (
                not player_summary
                and isinstance(cached_summary, dict)
                and cached_summary
            ):
                logger.info(
                    "No player summary available, using Player Cache as fallback"
                )
                html = cast("str", player_cache["profile"])
                return parse_player_stats_summary_from_html(
                    html, cached_summary, gamemode, platform
                )

        # Fetch from Blizzard using Blizzard ID
        logger.info(
            f"Player Cache not found or not up-to-date, fetching from Blizzard: {blizzard_id}"
        )
        html, _ = await fetch_player_html(client, blizzard_id)

        # Extract name from HTML for metadata
        name = extract_name_from_profile_html(html)

        # Parse stats
        data = parse_player_stats_summary_from_html(
            html, player_summary, gamemode, platform
        )

        # Update Player Cache with Blizzard ID as key
        # Progressive enhancement: if cache exists but is missing battletag, update it
        if player_cache and not player_cache.get("battletag") and battletag_input:
            logger.info(f"Updating cache with battletag metadata: {battletag_input}")

        await self.update_player_profile_cache(
            blizzard_id,
            player_summary,
            html,
            battletag=battletag_input,  # Optional metadata from user's request
            name=name,  # Display name extracted from HTML
        )

        return data
