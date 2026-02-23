"""Stateless parser functions for Blizzard heroes data"""

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
from app.heroes.enums import HeroGamemode

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort


async def fetch_heroes_html(
    client: BlizzardClientPort,
    locale: Locale = Locale.ENGLISH_US,
) -> str:
    """
    Fetch heroes list HTML from Blizzard

    Raises:
        HTTPException: If Blizzard returns non-200 status
    """

    url = f"{settings.blizzard_host}/{locale}{settings.heroes_path}"
    response = await client.get(url, headers={"Accept": "text/html"})
    validate_response_status(response)
    return response.text


def parse_heroes_html(html: str) -> list[dict]:
    """
    Parse heroes list HTML into structured data

    Args:
        html: Raw HTML content from Blizzard heroes page

    Returns:
        List of hero dicts with keys: key, name, portrait, role (sorted by key)

    Raises:
        ParserParsingError: If parsing fails
    """
    try:
        root_tag = parse_html_root(html)

        heroes = []
        for hero_element in root_tag.css("div.heroIndexWrapper blz-media-gallery a"):
            hero_url = safe_get_attribute(hero_element, "href")
            if not hero_url:
                msg = "Invalid hero URL"
                raise ParserParsingError(msg)

            name_element = hero_element.css_first("blz-card blz-content-block h2")
            portrait_element = hero_element.css_first("blz-card blz-image")

            gamemodes = [HeroGamemode.QUICKPLAY]
            if hero_element.css_matches("blz-card blz-badge.stadium-badge"):
                gamemodes.append(HeroGamemode.STADIUM)

            heroes.append(
                {
                    "key": hero_url.split("/")[-1],
                    "name": safe_get_text(name_element),
                    "portrait": safe_get_attribute(portrait_element, "src"),
                    "role": safe_get_attribute(hero_element, "data-role"),
                    "gamemodes": gamemodes,
                }
            )

        return sorted(heroes, key=lambda hero: hero["key"])

    except (AttributeError, KeyError, IndexError, TypeError) as error:
        error_msg = f"Failed to parse heroes HTML: {error!r}"
        raise ParserParsingError(error_msg) from error


def filter_heroes(
    heroes: list[dict], role: str | None, gamemode: HeroGamemode | None
) -> list[dict]:
    """Filter heroes list by role and gamemode"""
    if role:
        heroes = [hero for hero in heroes if hero["role"] == role]

    if gamemode:
        heroes = [hero for hero in heroes if gamemode in hero["gamemodes"]]

    return heroes


async def parse_heroes(
    client: BlizzardClientPort,
    locale: Locale = Locale.ENGLISH_US,
    role: str | None = None,
    gamemode: HeroGamemode | None = None,
) -> list[dict]:
    """
    High-level function to fetch and parse heroes list

    Args:
        client: Blizzard HTTP client
        locale: Blizzard page locale
        role: Optional role filter

    Returns:
        List of hero dicts, optionally filtered by role
    """
    html = await fetch_heroes_html(client, locale)
    heroes = parse_heroes_html(html)
    return filter_heroes(heroes, role, gamemode)
