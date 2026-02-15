"""Player Career Stats Controller module"""

from typing import TYPE_CHECKING, ClassVar, cast

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_career_stats import (
    parse_player_career_stats,
    parse_player_career_stats_from_html,
)
from app.adapters.blizzard.parsers.player_profile import fetch_player_html
from app.config import settings
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort
    from app.players.enums import PlayerGamemode, PlayerPlatform

from .base_player_controller import BasePlayerController, with_unknown_player_guard


class GetPlayerCareerStatsController(BasePlayerController):
    """Player Career Stats Controller used in order to retrieve career
    statistics of a player without labels, easily explorable
    """

    parser_classes: ClassVar[list] = []
    timeout = settings.career_path_cache_timeout

    @with_unknown_player_guard
    async def process_request(self, **kwargs) -> dict:
        """Process request with Player Cache support and unknown player guard"""
        player_id = kwargs["player_id"]
        platform = kwargs.get("platform")
        gamemode = kwargs.get("gamemode")
        hero = kwargs.get("hero")
        client = BlizzardClient()

        try:
            # Step 1: Resolve player identity (search + Blizzard ID resolution)
            # Returns player summary and optional cached HTML from resolution
            player_summary, cached_html = await self._resolve_player_identity(
                client, player_id
            )

            # Step 2: Fetch career stats with cache optimization
            # Pass cached_html to avoid redundant Blizzard call
            data = await self._fetch_career_stats_with_cache(
                client,
                player_id,
                player_summary,
                platform,
                gamemode,
                hero,
                cached_html=cached_html,
            )

        except ParserBlizzardError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail=error.message,
            ) from error
        except ParserParsingError as error:
            # Check if error message indicates player not found
            # This can happen when HTML structure is malformed or missing expected elements
            if "Could not find main content in HTML" in str(error):
                raise HTTPException(
                    status_code=404,
                    detail="Player not found",
                ) from error

            # Get Blizzard URL for error reporting
            blizzard_url = (
                f"{settings.blizzard_host}{settings.career_path}/"
                f"{player_summary['url'] if player_summary else player_id}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error

        # Update API Cache
        await self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data

    async def _fetch_career_stats_with_cache(
        self,
        client: BlizzardClientPort,
        player_id: str,
        player_summary: dict,
        platform: PlayerPlatform | None,
        gamemode: PlayerGamemode | None,
        hero: str | None,
        cached_html: str | None = None,
    ) -> dict:
        """Fetch player career stats with cache optimization.

        Implements Step 1 (use cached HTML) and Step 2 (BattleTag→Blizzard ID lookup).

        Args:
            client: Blizzard API client
            player_id: Player identifier
            player_summary: Player summary from search
            platform: Optional platform filter
            gamemode: Optional gamemode filter
            hero: Optional hero filter
            cached_html: HTML already fetched during identity resolution (Step 1 optimization)

        Returns:
            Player career stats data
        """
        # Step 1 optimization: Use cached HTML from _resolve_player_identity
        if cached_html:
            logger.info(
                "Using cached HTML from identity resolution (avoiding double-fetch)"
            )
            return parse_player_career_stats_from_html(
                cached_html, player_summary, platform, gamemode, hero
            )

        # No summary (Blizzard ID request or not in search) - fetch directly
        if not player_summary:
            logger.info("No summary available, fetching career stats from Blizzard")

            # Step 2 optimization: Check for cached Blizzard ID to skip redirects
            cached_blizzard_id = await self._get_blizzard_id_from_battletag(player_id)

            if cached_blizzard_id:
                logger.info(
                    f"Using cached Blizzard ID to skip redirects: {cached_blizzard_id}"
                )
                data, _ = await parse_player_career_stats(
                    client, cached_blizzard_id, None, platform, gamemode, hero
                )
            else:
                data, _ = await parse_player_career_stats(
                    client, player_id, None, platform, gamemode, hero
                )

            return data

        # Check Player Cache (SQLite storage)
        logger.info("Checking Player Cache...")
        player_cache = await self.get_player_profile_cache(player_id)

        if (
            player_cache is not None
            and player_cache["summary"]["lastUpdated"]  # ty: ignore[invalid-argument-type]
            == player_summary["lastUpdated"]
        ):
            logger.info("Player Cache found and up-to-date, using it")
            html = cast("str", player_cache["profile"])
            return parse_player_career_stats_from_html(
                html, player_summary, platform, gamemode, hero
            )

        # Fetch from Blizzard
        logger.info("Player Cache not found or not up-to-date, calling Blizzard")

        # Step 2 optimization: Use Blizzard ID from summary or cached mapping
        blizzard_id = player_summary.get("url")

        if not blizzard_id:
            # If summary doesn't have Blizzard ID (edge case), try cached
            blizzard_id = await self._get_blizzard_id_from_battletag(player_id)

        if blizzard_id:
            logger.info(f"Fetching career stats with Blizzard ID: {blizzard_id}")
            html, _ = await fetch_player_html(client, blizzard_id)
        else:
            logger.info(f"Fetching career stats with player ID: {player_id}")
            html, _ = await fetch_player_html(client, player_id)

        data = parse_player_career_stats_from_html(
            html, player_summary, platform, gamemode, hero
        )

        # Update Player Cache (SQLite storage)
        await self.update_player_profile_cache(player_id, player_summary, html)

        return data
