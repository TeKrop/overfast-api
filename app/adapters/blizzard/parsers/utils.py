"""Common utilities for Blizzard HTML/JSON parsing"""

import re
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from selectolax.lexbor import LexborHTMLParser, LexborNode

from app.exceptions import ParserParsingError
from app.overfast_logger import logger

if TYPE_CHECKING:
    import httpx


def validate_response_status(
    response: httpx.Response,
    valid_codes: list[int] | None = None,
) -> None:
    """
    Validate HTTP response status code

    Args:
        response: HTTP response from Blizzard
        valid_codes: List of valid status codes (default: [200])

    Raises:
        HTTPException: If status code is not valid
    """
    if valid_codes is None:
        valid_codes = [200]

    if response.status_code not in valid_codes:
        logger.error(
            "Received an error from Blizzard. HTTP {} : {}",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Couldn't get Blizzard page (HTTP {response.status_code} error) : {response.text}",
        )


def parse_html_root(html: str) -> LexborNode:
    """
    Parse HTML and return the root content node

    Args:
        html: Raw HTML string

    Returns:
        Root LexborNode (main-content or main element)

    Raises:
        ParserParsingError: If root node not found
    """
    parser = LexborHTMLParser(html)
    root_tag = parser.css_first("div.main-content,main")

    msg = "Could not find main content in HTML"
    if not root_tag:
        raise ParserParsingError(msg)

    return root_tag


def safe_get_text(node: LexborNode | None, default: str = "") -> str:
    """Safely get text from a node, return default if None"""
    return node.text().strip() if node else default


def safe_get_attribute(
    node: LexborNode | None,
    attribute: str,
    default: str = "",
) -> str | None:
    """Safely get attribute from a node, return default if None"""
    if not node or not node.attributes:
        return default
    return node.attributes.get(attribute, default)


def extract_blizzard_id_from_url(url: str) -> str | None:
    """
    Extract Blizzard ID from career profile URL (keeps URL-encoded format).

    Blizzard redirects BattleTag URLs to Blizzard ID URLs. The ID is kept
    in URL-encoded format to match the format used in search results.

    Examples:
        - Input: /career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f/
        - Output: df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f

    Args:
        url: Full URL or path from Blizzard profile redirect

    Returns:
        Blizzard ID string (URL-encoded), or None if not found
    """
    # Extract the path segment between /career/ and trailing /
    # Handle both full URLs and paths
    if "/career/" not in url:
        return None

    try:
        # Extract segment: /career/{ID}/ → {ID}
        career_segment = url.split("/career/")[1]
        blizzard_id = career_segment.rstrip("/").split("/")[0]

        # Return None if empty (malformed URL like "/career/")
        if not blizzard_id:
            return None
    except (IndexError, ValueError):
        logger.warning(f"Failed to extract Blizzard ID from URL: {url}")
        return None

    # Return as-is (URL-encoded) to match search results format
    return blizzard_id


def is_blizzard_id(player_id: str) -> bool:
    """
    Check if a player_id is a Blizzard ID (not a BattleTag).

    Blizzard IDs contain pipe character (| or %7C) and don't have hyphens.
    BattleTags have format: Name-12345

    Args:
        player_id: Player identifier to check

    Returns:
        True if player_id is a Blizzard ID, False if BattleTag

    Examples:
        >>> is_blizzard_id("TeKrop-2217")
        False
        >>> is_blizzard_id("df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f")
        True
        >>> is_blizzard_id("df51a381fe20caf8baa7|0bf3b4c47cbebe84b8db9c676a4e9c1f")
        True
    """
    # Blizzard IDs contain pipe (| or %7C), BattleTags have format Name-12345
    return ("%7C" in player_id or "|" in player_id) and "-" not in player_id


def is_battletag_id(player_id: str) -> bool:
    """
    Check if a player_id is a BattleTag with a discriminator (e.g. "Name-12345").

    Args:
        player_id: Player identifier to check

    Returns:
        True if player_id is in BattleTag format with a discriminator

    Examples:
        >>> is_battletag_id("TeKrop-2217")
        True
        >>> is_battletag_id("Player")
        False
        >>> is_battletag_id("df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f")
        False
    """
    return bool(re.fullmatch(r".+-\d{4,5}", player_id))


def match_player_by_blizzard_id(
    search_results: list[dict], blizzard_id: str
) -> dict | None:
    """
    Match a player from search results by Blizzard ID.

    Used to resolve ambiguous BattleTags when multiple players share the same name.

    Args:
        search_results: List of player dicts from Blizzard search endpoint
        blizzard_id: Blizzard ID extracted from profile redirect

    Returns:
        Matching player dict, or None if not found
    """
    for player in search_results:
        # Search results use "url" field for Blizzard ID
        if player.get("url") == blizzard_id:
            return player

    logger.warning(
        f"No player found in search results matching Blizzard ID: {blizzard_id}"
    )
    return None
