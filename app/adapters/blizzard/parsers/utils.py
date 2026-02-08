"""Common utilities for Blizzard HTML/JSON parsing"""

from typing import TYPE_CHECKING

from selectolax.lexbor import LexborHTMLParser, LexborNode

from app.exceptions import ParserParsingError

if TYPE_CHECKING:
    import httpx

    from app.adapters.blizzard.client import BlizzardClient


def validate_response_status(
    response: httpx.Response,
    client: BlizzardClient,
    valid_codes: list[int] | None = None,
) -> None:
    """
    Validate HTTP response status code

    Args:
        response: HTTP response from Blizzard
        client: BlizzardClient instance for error handling
        valid_codes: List of valid status codes (default: [200])

    Raises:
        HTTPException: If status code is not valid
    """
    if valid_codes is None:
        valid_codes = [200]

    if response.status_code not in valid_codes:
        raise client.blizzard_response_error_from_response(response)


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
) -> str:
    """Safely get attribute from a node, return default if None"""
    if not node or not node.attributes:
        return default
    return node.attributes.get(attribute, default)
