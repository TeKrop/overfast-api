"""Player Stats Summary Controller module"""

from typing import ClassVar

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_stats import parse_player_stats_summary
from app.adapters.blizzard.parsers.player_summary import parse_player_summary
from app.config import settings
from app.exceptions import ParserBlizzardError
from app.overfast_logger import logger

from .base_player_controller import BasePlayerController


class GetPlayerStatsSummaryController(BasePlayerController):
    """Player Stats Summary Controller used in order to retrieve essential
    stats of a player, often used for tracking progress : winrate, kda, damage, etc.
    Using the PlayerStatsSummaryParser.
    """

    parser_classes: ClassVar[list] = []
    timeout = settings.career_path_cache_timeout

    async def process_request(self, **kwargs) -> dict:
        """Process request with Player Cache support"""
        player_id = kwargs["player_id"]
        gamemode = kwargs.get("gamemode")
        platform = kwargs.get("platform")

        client = BlizzardClient()

        try:
            # Get player summary
            logger.info("Retrieving Player Summary...")
            player_summary = await parse_player_summary(client, player_id)

            # Check Player Cache if summary found
            if player_summary:
                logger.info("Checking Player Cache...")
                player_cache = self.cache_manager.get_player_cache(player_id)

                if (
                    player_cache is not None
                    and player_cache["summary"]["lastUpdated"]  # ty: ignore[invalid-argument-type]
                    == player_summary["lastUpdated"]
                ):
                    logger.info("Player Cache found and up-to-date")

            # Parse stats summary with aggregations
            data = await parse_player_stats_summary(
                client,
                player_id if not player_summary else player_summary["url"],
                player_summary,
                gamemode,
                platform,
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
