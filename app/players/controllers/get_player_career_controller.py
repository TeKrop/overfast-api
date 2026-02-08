"""Player Career Controller module"""

from typing import ClassVar

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_profile import (
    filter_all_stats_data,
    parse_player_profile_html,
)
from app.adapters.blizzard.parsers.player_summary import parse_player_summary
from app.config import settings
from app.exceptions import ParserBlizzardError
from app.overfast_logger import logger

from .base_player_controller import BasePlayerController


class GetPlayerCareerController(BasePlayerController):
    """Player Career Controller used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc.
    """

    parser_classes: ClassVar[list] = []
    timeout = settings.career_path_cache_timeout

    async def process_request(self, **kwargs) -> dict:
        """Process request with Player Cache support"""
        player_id = kwargs["player_id"]
        client = BlizzardClient()

        # Filters from query
        summary_filter = kwargs.get("summary")
        stats_filter = kwargs.get("stats")
        platform_filter = kwargs.get("platform")
        gamemode_filter = kwargs.get("gamemode")
        hero_filter = kwargs.get("hero")

        try:
            # Get player summary from search endpoint
            logger.info("Retrieving Player Summary...")
            player_summary = await parse_player_summary(client, player_id)

            # If player not found in search, fetch directly with player_id
            if not player_summary:
                logger.info("Player not found in search, fetching directly")
                html = await self._fetch_player_html(client, player_id)
                profile_data = parse_player_profile_html(html, None)
            else:
                # Check Player Cache
                logger.info("Checking Player Cache...")
                player_cache = self.cache_manager.get_player_cache(player_id)

                if (
                    player_cache is not None
                    and player_cache["summary"]["lastUpdated"]
                    == player_summary["lastUpdated"]
                ):
                    logger.info("Player Cache found and up-to-date, using it")
                    html = player_cache["profile"]
                    profile_data = parse_player_profile_html(html, player_summary)
                else:
                    # Fetch from Blizzard with Blizzard ID
                    logger.info(
                        "Player Cache not found or not up-to-date, calling Blizzard"
                    )
                    blizzard_id = player_summary["url"]
                    html = await self._fetch_player_html(client, blizzard_id)
                    profile_data = parse_player_profile_html(html, player_summary)

                    # Update Player Cache
                    self.cache_manager.update_player_cache(
                        player_id,
                        {"summary": player_summary, "profile": html},
                    )

            # Apply filters
            data = self._filter_profile_data(
                profile_data,
                summary_filter,
                stats_filter,
                platform_filter,
                gamemode_filter,
                hero_filter,
            )

        except ParserBlizzardError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail=error.message,
            ) from error
        except Exception as error:
            from app.exceptions import ParserParsingError
            from app.helpers import overfast_internal_error

            if isinstance(error, ParserParsingError):
                # Get Blizzard URL for error reporting
                blizzard_url = (
                    f"{settings.blizzard_host}{settings.career_path}/"
                    f"{player_summary.get('url', player_id) if player_summary else player_id}/"
                )
                raise overfast_internal_error(blizzard_url, error) from error
            raise

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data

    async def _fetch_player_html(self, client: BlizzardClient, player_id: str) -> str:
        """Fetch player HTML from Blizzard"""
        from app.adapters.blizzard.parsers.player_profile import fetch_player_html

        return await fetch_player_html(client, player_id)

    def _filter_profile_data(
        self,
        profile_data: dict,
        summary_filter: bool,
        stats_filter: bool,
        platform_filter: str | None,
        gamemode_filter: str | None,
        hero_filter: str | None,
    ) -> dict:
        """Apply query filters to profile data"""
        # If only summary requested
        if summary_filter:
            return profile_data.get("summary") or {}

        # If only stats requested
        if stats_filter:
            from app.adapters.blizzard.parsers.player_profile import (
                filter_stats_by_query,
            )

            return filter_stats_by_query(
                profile_data.get("stats"),
                platform_filter,
                gamemode_filter,
                hero_filter,
            )

        # Both summary and stats (with optional platform/gamemode filters)
        return {
            "summary": profile_data["summary"],
            "stats": filter_all_stats_data(
                profile_data.get("stats"),
                platform_filter,
                gamemode_filter,
            ),
        }
