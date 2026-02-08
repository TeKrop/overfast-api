"""Stateless parser functions for single hero details"""

import re
from typing import TYPE_CHECKING

from fastapi import status

from app.adapters.blizzard.client import BlizzardClient
from app.adapters.blizzard.parsers.utils import (
    parse_html_root,
    safe_get_attribute,
    safe_get_text,
    validate_response_status,
)
from app.config import settings
from app.enums import Locale
from app.exceptions import ParserBlizzardError
from app.heroes.enums import MediaType
from app.overfast_logger import logger
from app.roles.helpers import get_role_from_icon_url

if TYPE_CHECKING:
    from selectolax.lexbor import LexborNode


async def fetch_hero_html(
    client: BlizzardClient,
    hero_key: str,
    locale: Locale = Locale.ENGLISH_US,
) -> str:
    """Fetch single hero HTML from Blizzard"""
    url = f"{settings.blizzard_host}/{locale}{settings.heroes_path}{hero_key}/"
    response = await client.get(url, headers={"Accept": "text/html"})
    validate_response_status(response, client, valid_codes=[200, 404])
    return response.text


def parse_hero_html(html: str, locale: Locale = Locale.ENGLISH_US) -> dict:
    """
    Parse single hero details from HTML
    
    Args:
        html: Raw HTML content from Blizzard hero page
        locale: Locale for parsing birthday/age text
        
    Returns:
        Hero dict with name, description, role, location, birthday, age, abilities, story
        
    Raises:
        ParserBlizzardError: If hero not found (404)
    """
    root_tag = parse_html_root(html)
    
    # Check if hero exists
    abilities_section = root_tag.css_first("div.abilities-container")
    if not abilities_section:
        raise ParserBlizzardError(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Hero not found or not released yet",
        )
    
    overview_section = root_tag.css_first("blz-page-header")
    lore_section = root_tag.css_first("blz-section.lore")
    
    return {
        **_parse_hero_summary(overview_section, locale),
        "abilities": _parse_hero_abilities(abilities_section),
        "story": _parse_hero_story(lore_section),
    }


def _parse_hero_summary(overview_section: "LexborNode", locale: Locale) -> dict:
    """Parse hero summary section (name, role, location, birthday, age)"""
    header_section = overview_section.css_first("blz-header")
    extra_list_items = overview_section.css_first("blz-list").css("blz-list-item")
    
    birthday_text = safe_get_text(extra_list_items[2].css_first("p"))
    birthday, age = _parse_birthday_and_age(birthday_text, locale)
    
    icon_element = extra_list_items[0].css_first("blz-icon")
    icon_url = safe_get_attribute(icon_element, "src")
    
    return {
        "name": safe_get_text(header_section.css_first("h2")),
        "description": safe_get_text(header_section.css_first("p")),
        "role": get_role_from_icon_url(icon_url),
        "location": safe_get_text(extra_list_items[1]),
        "birthday": birthday,
        "age": age,
    }


def _parse_birthday_and_age(text: str, locale: Locale) -> tuple[str | None, int | None]:
    """Extract birthday and age from text for a given locale"""
    birthday_regex = r"^(.*) [\(（].*[:：] ?(\d+).*[\)）]$"
    
    result = re.match(birthday_regex, text)
    if not result:
        return None, None
    
    # Text for "Unknown" in different locales
    unknown_texts = {
        Locale.GERMAN: "Unbekannt",
        Locale.ENGLISH_EU: "Unknown",
        Locale.ENGLISH_US: "Unknown",
        Locale.SPANISH_EU: "Desconocido",
        Locale.SPANISH_LATIN: "Desconocido",
        Locale.FRENCH: "Inconnu",
        Locale.ITALIANO: "Sconosciuto",
        Locale.JAPANESE: "不明",
        Locale.KOREAN: "알 수 없음",
        Locale.POLISH: "Nieznane",
        Locale.PORTUGUESE_BRAZIL: "Desconhecido",
        Locale.RUSSIAN: "Неизвестно",
        Locale.CHINESE_TAIWAN: "未知",
    }
    unknown_text = unknown_texts.get(locale, "Unknown")
    
    birthday = result[1] if result[1] != unknown_text else None
    age = int(result[2]) if result[2] else None
    
    return birthday, age


def _parse_hero_abilities(abilities_section: "LexborNode") -> list[dict]:
    """Parse hero abilities section"""
    carousel_section_div = abilities_section.css_first("blz-carousel-section")
    abilities_list_div = carousel_section_div.css_first("blz-carousel")
    
    # Parse ability descriptions
    abilities_desc = [
        safe_get_text(desc_div.css_first("p")).replace("\r", "").replace("\n", " ")
        for desc_div in abilities_list_div.css("blz-feature")
    ]
    
    # Parse ability videos
    abilities_videos = [
        {
            "thumbnail": safe_get_attribute(video_div, "poster"),
            "link": {
                "mp4": safe_get_attribute(video_div, "mp4"),
                "webm": safe_get_attribute(video_div, "webm"),
            },
        }
        for video_div in carousel_section_div.css("blz-web-video")
    ]
    
    # Combine into abilities list
    abilities = []
    tab_controls = abilities_list_div.css_first("blz-tab-controls").css("blz-tab-control")
    for ability_index, ability_div in enumerate(tab_controls):
        abilities.append({
            "name": safe_get_attribute(ability_div, "label"),
            "description": abilities_desc[ability_index].strip(),
            "icon": safe_get_attribute(ability_div.css_first("blz-image"), "src"),
            "video": abilities_videos[ability_index],
        })
    
    return abilities


def _parse_hero_story(lore_section: "LexborNode") -> dict:
    """Parse hero story/lore section"""
    showcase_section = lore_section.css_first("blz-showcase")
    
    summary_text = safe_get_text(showcase_section.css_first("blz-header p"))
    summary = summary_text.replace("\n", "")
    
    accordion = lore_section.css_first("blz-accordion-section blz-accordion")
    
    return {
        "summary": summary,
        "media": _parse_hero_media(showcase_section),
        "chapters": _parse_story_chapters(accordion),
    }


def _parse_hero_media(showcase_section: "LexborNode") -> dict | None:
    """Parse hero media (video, comic, or short story)"""
    # Check for YouTube video
    if video := showcase_section.css_first("blz-youtube-video"):
        youtube_id = safe_get_attribute(video, "youtube-id")
        if youtube_id:
            return {
                "type": MediaType.VIDEO,
                "link": f"https://youtu.be/{youtube_id}",
            }
    
    # Check for button (comic or short story)
    if button := showcase_section.css_first("blz-button"):
        href = safe_get_attribute(button, "href")
        if not href:
            logger.warning("Missing href attribute in button element")
            return None
        
        analytics_label = safe_get_attribute(button, "analytics-label")
        media_type = (
            MediaType.SHORT_STORY
            if analytics_label == "short-story"
            else MediaType.COMIC
        )
        
        # Get full URL
        full_url = f"{settings.blizzard_host}{href}" if href.startswith("/") else href
        
        return {
            "type": media_type,
            "link": full_url,
        }
    
    return None


def _parse_story_chapters(accordion: "LexborNode") -> list[dict]:
    """Parse hero story chapters from accordion"""
    # Parse chapter content
    chapters_content = [
        " ".join([paragraph.text() for paragraph in content_container.css("p,pr")]).strip()
        for content_container in accordion.css("div[slot=content]")
    ]
    
    # Parse chapter pictures
    chapters_picture = [
        safe_get_attribute(picture, "src")
        for picture in accordion.css("blz-image")
    ]
    
    # Parse chapter titles
    titles = [node for node in accordion.iter() if node.tag == "span"]
    
    return [
        {
            "title": title_span.text().capitalize().strip(),
            "content": chapters_content[title_index],
            "picture": chapters_picture[title_index],
        }
        for title_index, title_span in enumerate(titles)
    ]


async def parse_hero(
    client: BlizzardClient,
    hero_key: str,
    locale: Locale = Locale.ENGLISH_US,
) -> dict:
    """
    High-level function to fetch and parse single hero
    
    Args:
        client: Blizzard HTTP client
        hero_key: Hero identifier (e.g., "ana", "mercy")
        locale: Blizzard page locale
        
    Returns:
        Complete hero data dict
    """
    html = await fetch_hero_html(client, hero_key, locale)
    return parse_hero_html(html, locale)
