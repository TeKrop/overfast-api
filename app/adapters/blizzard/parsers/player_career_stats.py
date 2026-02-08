"""Stateless parser for player career stats

This module provides simplified access to career stats extracted
from the full player profile data.
"""

from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.player_profile import (
    filter_stats_by_query,
    parse_player_profile,
)

if TYPE_CHECKING:
    from app.adapters.blizzard.client import BlizzardClient
    from app.players.enums import PlayerGamemode, PlayerPlatform


def extract_career_stats_from_profile(profile_data: dict) -> dict:
    """
    Extract career stats structure from full profile data

    Args:
        profile_data: Full profile dict with "summary" and "stats"

    Returns:
        Dict with "stats" key containing nested career stats structure
    """
    if not profile_data or not profile_data.get("stats"):
        return {}

    return {
        "stats": {
            platform: {
                gamemode: {
                    "career_stats": {
                        hero_key: (
                            {
                                stat_group["category"]: {
                                    stat["key"]: stat["value"]
                                    for stat in stat_group["stats"]
                                }
                                for stat_group in statistics
                            }
                            if statistics
                            else None
                        )
                        for hero_key, statistics in gamemode_stats[
                            "career_stats"
                        ].items()
                    },
                }
                for gamemode, gamemode_stats in platform_stats.items()
                if gamemode_stats
            }
            for platform, platform_stats in profile_data["stats"].items()
            if platform_stats
        },
    }


async def parse_player_career_stats(
    client: BlizzardClient,
    player_id: str,
    player_summary: dict | None = None,
    platform: PlayerPlatform | None = None,
    gamemode: PlayerGamemode | None = None,
    hero: str | None = None,
) -> dict:
    """
    Fetch and parse player career stats

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (Blizzard ID format)
        player_summary: Optional player summary from search endpoint
        platform: Optional platform filter
        gamemode: Optional gamemode filter
        hero: Optional hero filter

    Returns:
        Career stats dict, filtered by query parameters
    """
    # Fetch full profile
    profile_data = await parse_player_profile(client, player_id, player_summary)

    # Extract career stats structure
    career_stats_data = extract_career_stats_from_profile(profile_data)

    # Return stats only (no summary)
    if not career_stats_data:
        return {}

    # If filters provided, apply them
    if platform or gamemode or hero:
        stats = career_stats_data.get("stats")
        return filter_stats_by_query(stats, platform, gamemode, hero)

    return career_stats_data
