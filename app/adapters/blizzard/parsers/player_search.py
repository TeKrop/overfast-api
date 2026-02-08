"""Stateless parser for player search endpoint"""

from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.utils import validate_response_status
from app.config import settings
from app.overfast_logger import logger
from app.players.helpers import get_player_title

if TYPE_CHECKING:
    from app.adapters.blizzard.client import BlizzardClient


async def fetch_player_search_json(client: BlizzardClient, name: str) -> list[dict]:
    """
    Fetch player search results from Blizzard

    Args:
        client: Blizzard HTTP client
        name: Player name to search (may include discriminator)

    Returns:
        List of player dicts from Blizzard search
    """
    search_name = name.split("-", 1)[0]
    url = f"{settings.blizzard_host}{settings.search_account_path}/{search_name}/"

    response = await client.get(url)
    validate_response_status(response)

    return response.json()


def filter_players_by_name(json_data: list[dict], name: str) -> list[dict]:
    """
    Filter players by exact name match (case-sensitive, public only)

    Args:
        json_data: List of players from Blizzard
        name: Player name to filter (without discriminator)

    Returns:
        Filtered list of matching players
    """
    search_name = name.split("-", 1)[0]
    return [
        player
        for player in json_data
        if player["name"] == search_name and player["isPublic"] is True
    ]


def transform_player_search_results(
    players: list[dict],
    search_nickname: str,
) -> list[dict]:
    """
    Transform Blizzard player data to OverFast API format

    Args:
        players: Filtered list of players
        search_nickname: Original search input (may include discriminator)

    Returns:
        List of transformed player dicts
    """
    transformed_players = []

    for player in players:
        # If single result with discriminator in search, use search input as player_id
        player_id = (
            search_nickname
            if len(players) == 1 and "-" in search_nickname
            else player["url"]
        )

        # Normalize optional fields for regional consistency
        if player.get("portrait"):
            player["avatar"] = None
            player["namecard"] = None
            player["title"] = None

        transformed_players.append(
            {
                "player_id": player_id,
                "name": player["name"],
                "avatar": player["avatar"],
                "namecard": player.get("namecard"),
                "title": get_player_title(player.get("title")),
                "career_url": f"{settings.app_base_url}/players/{player_id}",
                "blizzard_id": player["url"],
                "last_updated_at": player["lastUpdated"],
                "is_public": player["isPublic"],
            },
        )

    return transformed_players


def apply_ordering(players: list[dict], order_by: str) -> list[dict]:
    """
    Sort players by specified field and direction

    Args:
        players: List of player dicts
        order_by: Ordering string (e.g., "name:asc", "last_updated_at:desc")

    Returns:
        Sorted list of players
    """
    order_field, order_arrangement = order_by.split(":")
    players.sort(
        key=lambda player: player[order_field],
        reverse=(order_arrangement == "desc"),
    )
    return players


def apply_pagination(players: list[dict], offset: int, limit: int) -> dict:
    """
    Apply pagination to player results

    Args:
        players: List of all matching players
        offset: Starting index
        limit: Maximum results to return

    Returns:
        Dict with total count and paginated results
    """
    return {
        "total": len(players),
        "results": players[offset : offset + limit],
    }


async def parse_player_search(
    client: BlizzardClient,
    name: str,
    order_by: str = "name:asc",
    offset: int = 0,
    limit: int = 10,
) -> dict:
    """
    High-level function to search for players

    Args:
        client: Blizzard HTTP client
        name: Player name to search
        order_by: Ordering (default: "name:asc")
        offset: Pagination offset (default: 0)
        limit: Pagination limit (default: 10)

    Returns:
        Dict with total count and paginated player results
    """
    logger.info("Fetching player search data from Blizzard...")
    json_data = await fetch_player_search_json(client, name)

    logger.info("Filtering players by name...")
    players = filter_players_by_name(json_data, name)

    logger.info("Applying transformation...")
    players = transform_player_search_results(players, name)

    logger.info("Applying ordering...")
    players = apply_ordering(players, order_by)

    logger.info("Done! Returning players list...")
    return apply_pagination(players, offset, limit)
