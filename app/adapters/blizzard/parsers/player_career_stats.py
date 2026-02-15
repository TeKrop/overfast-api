"""Stateless parser for player career stats

This module provides simplified access to career stats extracted
from the full player profile data.
"""

from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.player_profile import (
    filter_stats_by_query,
    parse_player_profile,
    parse_player_profile_html,
)

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort
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


def _process_career_stats(
    profile_data: dict,
    platform: PlayerPlatform | str | None = None,
    gamemode: PlayerGamemode | str | None = None,
    hero: str | None = None,
) -> dict:
    """
    Common logic to extract and filter career stats from profile data

    Args:
        profile_data: Full profile dict with "summary" and "stats"
        platform: Optional platform filter
        gamemode: Optional gamemode filter
        hero: Optional hero filter

    Returns:
        Career stats dict, filtered by query parameters
    """
    # Extract career stats structure
    career_stats_data = extract_career_stats_from_profile(profile_data)

    # Return empty if no stats
    if not career_stats_data:
        return {}

    # If filters provided, apply them
    if platform or gamemode or hero:
        stats = career_stats_data.get("stats")
        return filter_stats_by_query(stats, platform, gamemode, hero)

    return career_stats_data


def parse_player_career_stats_from_html(
    html: str,
    player_summary: dict | None = None,
    platform: PlayerPlatform | str | None = None,
    gamemode: PlayerGamemode | str | None = None,
    hero: str | None = None,
) -> dict:
    """
    Parse player career stats from HTML (for Player Cache usage)

    Args:
        html: Player profile HTML
        player_summary: Optional player summary from search endpoint
        platform: Optional platform filter
        gamemode: Optional gamemode filter
        hero: Optional hero filter

    Returns:
        Career stats dict, filtered by query parameters
    """
    profile_data = parse_player_profile_html(html, player_summary)
    return _process_career_stats(profile_data, platform, gamemode, hero)


async def parse_player_career_stats(
    client: BlizzardClientPort,
    player_id: str,
    player_summary: dict | None = None,
    platform: PlayerPlatform | str | None = None,
    gamemode: PlayerGamemode | str | None = None,
    hero: str | None = None,
) -> tuple[dict, str | None]:
    """
    Fetch and parse player career stats

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (Blizzard ID format or BattleTag)
        player_summary: Optional player summary from search endpoint
        platform: Optional platform filter
        gamemode: Optional gamemode filter
        hero: Optional hero filter

    Returns:
        Tuple of (career stats dict filtered by query parameters, Blizzard ID from redirect)
    """
    profile_data, blizzard_id = await parse_player_profile(
        client, player_id, player_summary
    )
    return _process_career_stats(profile_data, platform, gamemode, hero), blizzard_id
