"""Player Career Controller module"""

from typing import TYPE_CHECKING, ClassVar, cast

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_profile import (
    fetch_player_html,
    filter_all_stats_data,
    filter_stats_by_query,
    parse_player_profile_html,
)
from app.adapters.blizzard.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary_json,
)
from app.adapters.blizzard.parsers.utils import is_blizzard_id
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
    async def process_request(self, **kwargs) -> dict:  # noqa: PLR0915
        """Process request with Player Cache support and unknown player guard"""
        player_id = kwargs["player_id"]
        client = BlizzardClient()
        player_summary: dict | None = None
        blizzard_id: str | None = None
        search_json: list[dict] | None = None

        # Filters from query
        summary_filter = bool(kwargs.get("summary"))
        stats_filter = bool(kwargs.get("stats"))
        platform_filter = kwargs.get("platform")
        gamemode_filter = kwargs.get("gamemode")
        hero_filter = kwargs.get("hero")

        try:
            # Get player summary from search endpoint (unless player_id is Blizzard ID)
            logger.info("Retrieving Player Summary...")

            # Skip search if player_id is a Blizzard ID
            if not is_blizzard_id(player_id):
                search_json = await fetch_player_summary_json(client, player_id)
                player_summary = parse_player_summary_json(search_json, player_id)
                logger.info("Player Summary retrieved !")

            # If player not found in search, fetch profile to resolve
            if not player_summary:
                logger.info("Player not found in search, fetching profile to resolve")
                html, blizzard_id = await self._fetch_player_html(client, player_id)
                profile_data = parse_player_profile_html(html, None)

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
                        # Re-parse with complete summary for better data
                        profile_data = parse_player_profile_html(html, player_summary)
                        # Update cache with complete profile + summary
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
                    profile_data = parse_player_profile_html(html, player_summary)
                else:
                    # Fetch from Blizzard with Blizzard ID
                    logger.info(
                        "Player Cache not found or not up-to-date, calling Blizzard"
                    )
                    blizzard_id = player_summary["url"]
                    html, _ = await self._fetch_player_html(client, blizzard_id)
                    profile_data = parse_player_profile_html(html, player_summary)

                    # Update Player Cache (SQLite storage)
                    await self.update_player_profile_cache(
                        player_id, player_summary, html
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
                f"{player_summary.get('url', player_id) if player_summary else player_id}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error

        # Update API Cache
        await self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data

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
