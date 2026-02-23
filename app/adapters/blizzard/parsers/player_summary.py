"""Stateless parser for player summary data from Blizzard search endpoint"""

from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.utils import (
    is_blizzard_id,
    match_player_by_blizzard_id,
    validate_response_status,
)
from app.config import settings
from app.exceptions import ParserParsingError
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort


async def fetch_player_summary_json(
    client: BlizzardClientPort, player_id: str
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


def parse_player_summary_json(
    json_data: list[dict], player_id: str, blizzard_id: str | None = None
) -> dict:
    """
    Parse player summary from search endpoint JSON

    Args:
        json_data: List of player data from Blizzard search
        player_id: Player ID to find (BattleTag format)
        blizzard_id: Optional Blizzard ID from profile redirect to resolve ambiguity

    Returns:
        Player summary dict, or empty dict if not found

    Raises:
        ParserParsingError: If unexpected payload structure
    """

    try:
        player_name = player_id.split("-", 1)[0]

        # Find matching players (exact name match, case-sensitive, public only)
        matching_players = [
            player
            for player in json_data
            if player["name"] == player_name and player["isPublic"] is True
        ]

        if blizzard_id:
            # Blizzard ID provided: always use it to verify the match, regardless
            # of how many name-matching players were found. This prevents accepting
            # a wrong player even when there is only one name match.
            if len(matching_players) > 1:
                logger.info(
                    f"Multiple players found for {player_id}, using Blizzard ID to resolve: {blizzard_id}"
                )
            player_data = match_player_by_blizzard_id(matching_players, blizzard_id)
            if not player_data:
                logger.warning(
                    f"Blizzard ID {blizzard_id} not found in search results for {player_id}"
                )
                return {}
        elif len(matching_players) == 1:
            player_data = matching_players[0]
            # When the player_id contains a discriminator (BattleTag format like
            # "Progresso-2749"), validate that the search result actually corresponds
            # to this specific player. Without this check, a different player sharing
            # the same name (e.g. "Progresso-1234") could be silently returned.
            #
            # Validation is only possible when the result URL is in BattleTag format
            # (i.e. not a Blizzard ID). If the URL is a Blizzard ID we cannot confirm
            # the discriminator without the redirect, so we return {} and let the
            # caller fall through to redirect-based identity resolution.
            if "-" in player_id:
                player_url = player_data.get("url", "")
                if is_blizzard_id(player_url) or player_url != player_id:
                    logger.warning(
                        "Player {} not found or unverifiable: "
                        "search returned player with URL {} instead",
                        player_id,
                        player_url,
                    )
                    return {}
        else:
            # Player not found or multiple matches without Blizzard ID
            logger.warning(
                "Player {} not found in search results ({} matching players)",
                player_id,
                len(matching_players),
            )
            return {}

        # Normalize optional fields for regional consistency
        # Some regions still use "portrait" instead of "avatar", "namecard", "title"
        if player_data.get("portrait"):
            player_data["avatar"] = None
            player_data["namecard"] = None
            player_data["title"] = None

    except (KeyError, TypeError) as error:
        msg = f"Unexpected Blizzard search payload structure: {error}"
        raise ParserParsingError(msg) from error
    else:
        return player_data


async def parse_player_summary(
    client: BlizzardClientPort, player_id: str, blizzard_id: str | None = None
) -> dict:
    """
    High-level function to fetch and parse player summary

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (BattleTag format or Blizzard ID)
        blizzard_id: Optional Blizzard ID from profile redirect to resolve ambiguity

    Returns:
        Player summary dict with url, lastUpdated, avatar, etc.
        Empty dict if player not found, multiple matches without Blizzard ID,
        or if player_id is a Blizzard ID (search doesn't work with IDs)

    Raises:
        ParserParsingError: If unexpected payload structure
    """
    # If player_id is a Blizzard ID, skip search (won't find anything useful)
    if is_blizzard_id(player_id):
        logger.info(
            f"Player ID {player_id} is a Blizzard ID, skipping search (not supported)"
        )
        return {}

    json_data = await fetch_player_summary_json(client, player_id)
    return parse_player_summary_json(json_data, player_id, blizzard_id)
