"""Stateless parser functions for hero stats summary (pickrate/winrate from Blizzard API)"""

from http import HTTPStatus
from typing import TYPE_CHECKING

from app.config import settings
from app.domain.enums import PlayerGamemode, PlayerPlatform, PlayerRegion
from app.domain.exceptions import (
    InvalidGamemodeFilterError,
    ParserBlizzardError,
    ParserParsingError,
)
from app.domain.parsers.utils import validate_response_status

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort

# Mappings for query parameters
PLATFORM_MAPPING: dict[PlayerPlatform, str] = {
    PlayerPlatform.PC: "PC",
    PlayerPlatform.CONSOLE: "Console",
}


async def fetch_hero_stats_json(
    client: BlizzardClientPort,
    platform: PlayerPlatform,
    gamemode: PlayerGamemode,
    gamemode_filter: str,
    region: PlayerRegion,
    map_filter: str = "all-maps",
    competitive_division: str | None = None,
) -> dict:
    """Fetch hero stats JSON from Blizzard API

    As gamemode filter values are dynamically changing on Blizzard side,
    both gamemode and gamemode_filter are needed to properly build query params
    """
    url = f"{settings.blizzard_host}{settings.hero_stats_path}"

    # Build query params
    query_params = {
        "input": PLATFORM_MAPPING[platform],
        "rq": gamemode_filter,
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
    validate_response_status(response)

    return response.json()


def parse_hero_stats_json(
    json_data: dict,
    map_filter: str,
    gamemode: PlayerGamemode,
    gamemode_filter: str,
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
    # Extract top-level structure; raise ParserParsingError on unexpected shape.
    try:
        # Blizzard now wraps the payload under a top-level "rates" object;
        # the previous "selected" and "rates" keys live inside it.
        rates_payload = json_data["rates"]
        selected_map = rates_payload["selected"]["map"]
        selected_gamemode = rates_payload["selected"]["rq"]
        rates = rates_payload["rates"]
    except (KeyError, TypeError) as error:
        msg = f"Unexpected Blizzard hero stats JSON structure: {error!r}"
        raise ParserParsingError(msg) from error

    # Validate gamemode filter against selected according to Blizzard response
    # Could be invalid if Blizzard filtering value has changed, it happened
    # several times for competitive in past few months
    if gamemode_filter != selected_gamemode:
        msg = (
            f"Gamemode filter '{gamemode_filter}' is different from "
            f"selected gamemode '{selected_gamemode}'"
        )
        raise InvalidGamemodeFilterError(msg)

    # Validate map matches gamemode (outside try so this is never caught above).
    if map_filter != selected_map:
        raise ParserBlizzardError(
            status_code=HTTPStatus.BAD_REQUEST.value,
            message=f"Selected map '{map_filter}' is not compatible with '{gamemode}' gamemode.",
        )

    # Filter by role and transform to simplified format; raise ParserParsingError on
    # unexpected per-entry shape.
    try:
        hero_stats = [
            rate
            for rate in rates
            if role_filter is None or rate["hero"]["role"].lower() == role_filter
        ]
        hero_stats = [
            {
                "hero": rate["id"],
                "pickrate": _normalize_rate(rate["cells"]["pickrate"]),
                "winrate": _normalize_rate(rate["cells"]["winrate"]),
            }
            for rate in hero_stats
        ]
    except (KeyError, TypeError) as error:
        msg = f"Unexpected Blizzard hero stats JSON structure: {error!r}"
        raise ParserParsingError(msg) from error

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
    client: BlizzardClientPort,
    platform: PlayerPlatform,
    gamemode: PlayerGamemode,
    gamemode_filter: str,
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
        gamemode_filter,
        region,
        map_key,
        competitive_division,
    )

    return parse_hero_stats_json(
        json_data, map_key, gamemode, gamemode_filter, role, order_by
    )
