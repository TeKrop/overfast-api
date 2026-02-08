"""Stateless parser functions for hero stats summary (pickrate/winrate from Blizzard API)"""

from fastapi import status

from app.adapters.blizzard.client import BlizzardClient
from app.adapters.blizzard.parsers.utils import validate_response_status
from app.config import settings
from app.exceptions import ParserBlizzardError
from app.players.enums import PlayerGamemode, PlayerPlatform, PlayerRegion

# Mappings for query parameters
PLATFORM_MAPPING: dict[PlayerPlatform, str] = {
    PlayerPlatform.PC: "PC",
    PlayerPlatform.CONSOLE: "Console",
}

GAMEMODE_MAPPING: dict[PlayerGamemode, str] = {
    PlayerGamemode.QUICKPLAY: "0",
    PlayerGamemode.COMPETITIVE: "1",
}


async def fetch_hero_stats_json(
    client: BlizzardClient,
    platform: PlayerPlatform,
    gamemode: PlayerGamemode,
    region: PlayerRegion,
    map_filter: str = "all-maps",
    competitive_division: str | None = None,
) -> dict:
    """Fetch hero stats JSON from Blizzard API"""
    url = f"{settings.blizzard_host}{settings.hero_stats_path}"

    # Build query params
    query_params = {
        "input": PLATFORM_MAPPING[platform],
        "rq": GAMEMODE_MAPPING[gamemode],
        "region": region.capitalize(),
        "map": map_filter,
    }

    if gamemode == PlayerGamemode.COMPETITIVE:
        tier = (competitive_division or "all").capitalize()
        query_params["tier"] = tier

    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }

    response = await client.get(url, headers=headers, params=query_params)
    validate_response_status(response, client)

    return response.json()


def parse_hero_stats_json(
    json_data: dict,
    map_filter: str,
    gamemode: PlayerGamemode,
    role_filter: str | None = None,
    order_by: str = "hero:asc",
) -> list[dict]:
    """
    Parse and filter hero stats from JSON

    Args:
        json_data: Raw JSON response from Blizzard API
        map_filter: Map filter applied
        gamemode: Gamemode for validation
        role_filter: Optional role to filter by
        order_by: Ordering field and direction (e.g., "pickrate:desc")

    Returns:
        List of hero stats dicts with hero, pickrate, winrate

    Raises:
        ParserBlizzardError: If map doesn't match gamemode
    """
    # Validate map matches gamemode
    if map_filter != json_data["selected"]["map"]:
        raise ParserBlizzardError(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Selected map '{map_filter}' is not compatible with '{gamemode}' gamemode.",
        )

    # Filter by role if provided
    hero_stats = [
        rate
        for rate in json_data["rates"]
        if role_filter is None or rate["hero"]["role"].lower() == role_filter
    ]

    # Transform to simplified format
    hero_stats = [
        {
            "hero": rate["id"],
            "pickrate": _normalize_rate(rate["cells"]["pickrate"]),
            "winrate": _normalize_rate(rate["cells"]["winrate"]),
        }
        for rate in hero_stats
    ]

    # Apply ordering
    order_field, order_arrangement = order_by.split(":")
    hero_stats.sort(
        key=lambda stat: stat[order_field],
        reverse=(order_arrangement == "desc"),
    )

    return hero_stats


def _normalize_rate(rate: float) -> float:
    """
    Normalize rate value (convert -1 to 0.0)

    Blizzard returns -1 when data isn't available, we convert to 0.0
    """
    return rate if rate != -1 else 0.0


async def parse_hero_stats_summary(
    client: BlizzardClient,
    platform: PlayerPlatform,
    gamemode: PlayerGamemode,
    region: PlayerRegion,
    role: str | None = None,
    map_filter: str | None = None,
    competitive_division: str | None = None,
    order_by: str = "hero:asc",
) -> list[dict]:
    """
    High-level function to fetch and parse hero stats summary

    Args:
        client: Blizzard HTTP client
        platform: PC or Console
        gamemode: Quickplay or Competitive
        region: Player region
        role: Optional role filter
        map_filter: Optional map filter (defaults to "all-maps")
        competitive_division: Optional competitive division filter
        order_by: Ordering (e.g., "pickrate:desc", "hero:asc")

    Returns:
        List of hero stats dicts
    """
    map_key = map_filter or "all-maps"

    json_data = await fetch_hero_stats_json(
        client,
        platform,
        gamemode,
        region,
        map_key,
        competitive_division,
    )

    return parse_hero_stats_json(json_data, map_key, gamemode, role, order_by)
