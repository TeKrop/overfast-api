"""Player Career Stats Controller module"""

from typing import ClassVar, cast

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_career_stats import (
    parse_player_career_stats,
    parse_player_career_stats_from_html,
)
from app.adapters.blizzard.parsers.player_profile import fetch_player_html
from app.adapters.blizzard.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary_json,
)
from app.adapters.blizzard.parsers.utils import is_blizzard_id
from app.config import settings
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error
from app.overfast_logger import logger

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
        player_summary: dict | None = None
        blizzard_id: str | None = None
        search_json: list[dict] | None = None

        try:
            # Get player summary (unless player_id is Blizzard ID)
            logger.info("Retrieving Player Summary...")

            # Skip search if player_id is a Blizzard ID
            if not is_blizzard_id(player_id):
                search_json = await fetch_player_summary_json(client, player_id)
                player_summary = parse_player_summary_json(search_json, player_id)

            # If player not found in search, fetch profile to resolve
            if not player_summary:
                logger.info("Player not found in search, fetching profile to resolve")
                data, blizzard_id = await parse_player_career_stats(
                    client,
                    player_id,
                    None,
                    platform,
                    gamemode,
                    hero,
                )

                # If we got a Blizzard ID and have search results, retry parsing with it
                if blizzard_id and search_json:
                    logger.info(
                        f"Got Blizzard ID from redirect: {blizzard_id}, re-parsing search results"
                    )
                    player_summary = parse_player_summary_json(
                        search_json, player_id, blizzard_id
                    )

                    if player_summary:
                        logger.info("Successfully resolved player via Blizzard ID")
                        # Update cache with complete profile + summary
                        html, _ = await fetch_player_html(client, blizzard_id)
                        await self.update_player_profile_cache(
                            player_id, player_summary, html
                        )
                    else:
                        logger.warning(
                            "Could not resolve player even with Blizzard ID from redirect"
                        )
            else:
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
                    data = parse_player_career_stats_from_html(
                        html,
                        player_summary,
                        platform,
                        gamemode,
                        hero,
                    )
                else:
                    # Fetch from Blizzard with Blizzard ID
                    logger.info(
                        "Player Cache not found or not up-to-date, calling Blizzard"
                    )
                    blizzard_id = player_summary["url"]
                    html, _ = await fetch_player_html(client, blizzard_id)
                    data = parse_player_career_stats_from_html(
                        html,
                        player_summary,
                        platform,
                        gamemode,
                        hero,
                    )

                    # Update Player Cache (SQLite storage)
                    await self.update_player_profile_cache(
                        player_id, player_summary, html
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
