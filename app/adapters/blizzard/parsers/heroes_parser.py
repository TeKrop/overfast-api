"""Stateless parser functions for Blizzard heroes data"""

from selectolax.lexbor import LexborHTMLParser, LexborNode

from app.adapters.blizzard.client import BlizzardClient
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
        HTTPException: If Blizzard returns an error status code
    """
    url = f"{settings.blizzard_host}/{locale}{settings.heroes_path}"
    response = await client.get(url, headers={"Accept": "text/html"})
    
    # Check for valid HTTP status
    if response.status_code != 200:
        # BlizzardClient already handles this in its get() method,
        # but if somehow we get here, raise the error
        from fastapi import status as http_status
        from fastapi import HTTPException
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Couldn't get Blizzard page (HTTP {response.status_code} error) : {response.text}",
        )
    
    return response.text


def parse_heroes_html(html: str) -> list[dict]:
    """
    Parse heroes list HTML into structured data
    
    Args:
        html: Raw HTML content from Blizzard heroes page
        
    Returns:
        List of hero dicts with keys: key, name, portrait, role
        
    Raises:
        ParserParsingError: If parsing fails
    """
    try:
        parser = LexborHTMLParser(html)
        root_tag = parser.css_first("div.main-content,main")
        
        if not root_tag:
            raise ParserParsingError("Could not find main content in heroes HTML")
        
        heroes = []
        for hero_element in root_tag.css("div.heroIndexWrapper blz-media-gallery a"):
            hero_url = hero_element.attributes.get("href")
            if not hero_url:
                raise ParserParsingError("Invalid hero URL")
            
            name_element = hero_element.css_first("blz-card blz-content-block h2")
            portrait_element = hero_element.css_first("blz-card blz-image")
            
            heroes.append({
                "key": hero_url.split("/")[-1],
                "name": name_element.text() if name_element else "",
                "portrait": portrait_element.attributes.get("src", "") if portrait_element else "",
                "role": hero_element.attributes.get("data-role", ""),
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
