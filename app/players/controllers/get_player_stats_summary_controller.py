"""Player Stats Summary Controller module"""

from typing import ClassVar

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_profile import fetch_player_html
from app.adapters.blizzard.parsers.player_stats import (
    parse_player_stats_summary,
    parse_player_stats_summary_from_html,
)
from app.adapters.blizzard.parsers.player_summary import parse_player_summary
from app.config import settings
from app.exceptions import ParserBlizzardError
from app.overfast_logger import logger

from .base_player_controller import BasePlayerController


class GetPlayerStatsSummaryController(BasePlayerController):
    """Player Stats Summary Controller used in order to retrieve essential
    stats of a player, often used for tracking progress: winrate, kda, damage, etc.
    """

    parser_classes: ClassVar[list] = []
    timeout = settings.career_path_cache_timeout

    async def process_request(self, **kwargs) -> dict:
        """Process request with Player Cache support"""
        player_id = kwargs["player_id"]
        gamemode = kwargs.get("gamemode")
        platform = kwargs.get("platform")

        client = BlizzardClient()
        player_summary: dict | None = None

        try:
            # Get player summary
            logger.info("Retrieving Player Summary...")
            player_summary = await parse_player_summary(client, player_id)

            # If player not found in search, fetch directly with player_id
            if not player_summary:
                logger.info("Player not found in search, fetching directly")
                data = await parse_player_stats_summary(
                    client,
                    player_id,
                    None,
                    gamemode,
                    platform,
                )
            else:
                # Check Player Cache
                logger.info("Checking Player Cache...")
                player_cache = self.cache_manager.get_player_cache(player_id)

                if (
                    player_cache is not None
                    and player_cache["summary"]["lastUpdated"]  # ty: ignore[invalid-argument-type]
                    == player_summary["lastUpdated"]
                ):
                    logger.info("Player Cache found and up-to-date, using it")
                    html = player_cache["profile"]  # ty: ignore[invalid-argument-type]
                    data = parse_player_stats_summary_from_html(
                        html,
                        player_summary,
                        gamemode,
                        platform,
                    )
                else:
                    # Fetch from Blizzard with Blizzard ID
                    logger.info(
                        "Player Cache not found or not up-to-date, calling Blizzard"
                    )
                    blizzard_id = player_summary["url"]
                    html = await fetch_player_html(client, blizzard_id)
                    data = parse_player_stats_summary_from_html(
                        html,
                        player_summary,
                        gamemode,
                        platform,
                    )

                    # Update Player Cache
                    self.cache_manager.update_player_cache(
                        player_id,
                        {"summary": player_summary, "profile": html},
                    )

        except ParserBlizzardError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail=error.message,
            ) from error

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
