"""Common utilities for Blizzard HTML/JSON parsing"""

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
