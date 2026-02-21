"""Stateless parser functions for roles data"""

from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.utils import (
    parse_html_root,
    safe_get_attribute,
    safe_get_text,
    validate_response_status,
)
from app.config import settings
from app.enums import Locale
from app.exceptions import ParserParsingError
from app.roles.helpers import get_role_from_icon_url

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort


async def fetch_roles_html(
    client: BlizzardClientPort,
    locale: Locale = Locale.ENGLISH_US,
) -> str:
    """Fetch roles HTML from Blizzard homepage"""
    url = f"{settings.blizzard_host}/{locale}{settings.home_path}"
    response = await client.get(url, headers={"Accept": "text/html"})
    validate_response_status(response)
    return response.text


def parse_roles_html(html: str) -> list[dict]:
    """
    Parse roles from Blizzard homepage HTML

    Returns:
        List of role dicts with keys: key, name, icon, description

    Raises:
        ParserParsingError: If HTML structure is unexpected
    """
    try:
        root_tag = parse_html_root(html)

        roles_container = root_tag.css_first(
            "div.homepage-features-heroes blz-feature-carousel-section"
        )

        if not roles_container:
            msg = "Roles container not found in homepage HTML"
            raise ParserParsingError(msg)

        # Get all role icons
        tab_controls = roles_container.css_first("blz-tab-controls")
        if not tab_controls:
            msg = "Role tab controls not found in homepage HTML"
            raise ParserParsingError(msg)

        roles_icons = [
            safe_get_attribute(role_icon_div.css_first("blz-image"), "src")
            for role_icon_div in tab_controls.css("blz-tab-control")
        ]

        # Parse role details
        roles = []
        role_features = roles_container.css("blz-feature")
        for role_index, role_div in list(enumerate(role_features))[:3]:
            header = role_div.css_first("blz-header")
            if not header:
                msg = f"Role header not found for role index {role_index}"
                raise ParserParsingError(msg)

            roles.append(
                {
                    "key": get_role_from_icon_url(roles_icons[role_index]),
                    "name": safe_get_text(header.css_first("h3")).capitalize(),
                    "icon": roles_icons[role_index],
                    "description": safe_get_text(header.css_first("div")),
                }
            )

    except (AttributeError, KeyError, IndexError, TypeError) as error:
        msg = f"Unexpected Blizzard homepage structure: {error}"
        raise ParserParsingError(msg) from error
    else:
        return roles


async def parse_roles(
    client: BlizzardClientPort,
    locale: Locale = Locale.ENGLISH_US,
) -> list[dict]:
    """
    High-level function to fetch and parse roles

    Returns:
        List of role dicts

    Raises:
        ParserParsingError: If HTML structure is unexpected
    """
    html = await fetch_roles_html(client, locale)
    return parse_roles_html(html)
