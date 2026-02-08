"""Stateless parser for player summary data from Blizzard search endpoint"""

from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.utils import validate_response_status
from app.config import settings
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.adapters.blizzard.client import BlizzardClient


async def fetch_player_summary_json(
    client: BlizzardClient, player_id: str
) -> list[dict]:
    """
    Fetch player summary data from Blizzard search endpoint

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (name-discriminator format)

    Returns:
        Raw JSON response from Blizzard (list of player dicts)
    """
    player_name = player_id.split("-", 1)[0]
    url = f"{settings.blizzard_host}{settings.search_account_path}/{player_name}/"

    response = await client.get(url)
    validate_response_status(response)

    return response.json()


def parse_player_summary_json(json_data: list[dict], player_id: str) -> dict:
    """
    Parse player summary from search endpoint JSON

    Args:
        json_data: List of player data from Blizzard search
        player_id: Player ID to find

    Returns:
        Player summary dict, or empty dict if not found uniquely
    """
    player_name = player_id.split("-", 1)[0]

    # Find matching players (exact name match, case-sensitive, public only)
    matching_players = [
        player
        for player in json_data
        if player["name"] == player_name and player["isPublic"] is True
    ]

    if len(matching_players) != 1:
        # Player not found or multiple matches
        logger.warning(
            "Player {} not found in search results ({} matching players)",
            player_id,
            len(matching_players),
        )
        return {}

    player_data = matching_players[0]

    # Normalize optional fields for regional consistency
    # Some regions still use "portrait" instead of "avatar", "namecard", "title"
    if player_data.get("portrait"):
        player_data["avatar"] = None
        player_data["namecard"] = None
        player_data["title"] = None

    return player_data


async def parse_player_summary(client: BlizzardClient, player_id: str) -> dict:
    """
    High-level function to fetch and parse player summary

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (name-discriminator format)

    Returns:
        Player summary dict with url, lastUpdated, avatar, etc.
        Empty dict if player not found
    """
    json_data = await fetch_player_summary_json(client, player_id)
    return parse_player_summary_json(json_data, player_id)
