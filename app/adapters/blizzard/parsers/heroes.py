"""Stateless parser functions for Blizzard heroes data"""

from app.adapters.blizzard.client import BlizzardClient
from app.adapters.blizzard.parsers.utils import parse_html_root, safe_get_attribute, safe_get_text
from app.config import settings
from app.enums import Locale
from app.exceptions import ParserParsingError


async def fetch_heroes_html(
    client: BlizzardClient,
    locale: Locale = Locale.ENGLISH_US,
) -> str:
    """
    Fetch heroes list HTML from Blizzard
    
    Raises:
        HTTPException: If Blizzard returns non-200 status
    """
    from app.adapters.blizzard.parsers.utils import validate_response_status
    
    url = f"{settings.blizzard_host}/{locale}{settings.heroes_path}"
    response = await client.get(url, headers={"Accept": "text/html"})
    validate_response_status(response, client)
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
                raise ParserParsingError("Invalid hero URL")
            
            name_element = hero_element.css_first("blz-card blz-content-block h2")
            portrait_element = hero_element.css_first("blz-card blz-image")
            
            heroes.append({
                "key": hero_url.split("/")[-1],
                "name": safe_get_text(name_element),
                "portrait": safe_get_attribute(portrait_element, "src"),
                "role": safe_get_attribute(hero_element, "data-role"),
            })
        
        return sorted(heroes, key=lambda hero: hero["key"])
    
    except (AttributeError, KeyError, IndexError, TypeError) as error:
        raise ParserParsingError(f"Failed to parse heroes HTML: {error!r}") from error


def filter_heroes_by_role(heroes: list[dict], role: str | None) -> list[dict]:
    """Filter heroes list by role"""
    if not role:
        return heroes
    return [hero for hero in heroes if hero["role"] == role]


async def parse_heroes(
    client: BlizzardClient,
    locale: Locale = Locale.ENGLISH_US,
    role: str | None = None,
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
    return filter_heroes_by_role(heroes, role)
