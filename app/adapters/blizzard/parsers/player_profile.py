"""Stateless parser for player profile data from Blizzard career page

This module handles parsing of player profile HTML including:
- Player summary (username, avatar, title, endorsement, competitive ranks)
- Player stats across platforms, gamemodes, and heroes
- Heroes comparisons (top heroes by category)
- Career stats (detailed statistics per hero)
"""

from typing import TYPE_CHECKING

from fastapi import status

from app.adapters.blizzard.client import BlizzardClient
from app.adapters.blizzard.parsers.utils import (
    parse_html_root,
    validate_response_status,
)
from app.config import settings
from app.exceptions import ParserBlizzardError
from app.overfast_logger import logger
from app.players.enums import (
    CareerHeroesComparisonsCategory,
    CompetitiveRole,
    PlayerGamemode,
    PlayerPlatform,
)
from app.players.helpers import (
    get_computed_stat_value,
    get_division_from_icon,
    get_endorsement_value_from_frame,
    get_hero_keyname,
    get_player_title,
    get_plural_stat_key,
    get_real_category_name,
    get_role_key_from_icon,
    get_stats_hero_class,
    get_tier_from_icon,
    string_to_snakecase,
)

if TYPE_CHECKING:
    from selectolax.lexbor import LexborNode

# Platform/gamemode CSS class mappings
PLATFORMS_DIV_MAPPING = {
    PlayerPlatform.PC: "mouseKeyboard-view",
    PlayerPlatform.CONSOLE: "controller-view",
}
GAMEMODES_DIV_MAPPING = {
    PlayerGamemode.QUICKPLAY: "quickPlay-view",
    PlayerGamemode.COMPETITIVE: "competitive-view",
}


async def fetch_player_html(client: BlizzardClient, player_id: str) -> str:
    """
    Fetch player profile HTML from Blizzard

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (Blizzard ID format)

    Returns:
        Raw HTML content

    Raises:
        ParserBlizzardError: If player not found (404)
    """
    url = f"{settings.blizzard_host}{settings.career_path}/{player_id}/"

    response = await client.get(url)
    validate_response_status(response, client, valid_codes=[200, 404])

    return response.text


def parse_player_profile_html(
    html: str,
    player_summary: dict | None = None,
) -> dict:
    """
    Parse player profile HTML into summary and stats

    Args:
        html: Raw HTML from player profile page
        player_summary: Optional player summary data from search endpoint
            (provides avatar, namecard, title, lastUpdated)

    Returns:
        Dict with "summary" and "stats" keys

    Raises:
        ParserBlizzardError: If player not found (profile section missing)
    """
    root_tag = parse_html_root(html)

    # Check if player exists
    if not root_tag.css_first("blz-section.Profile-masthead"):
        raise ParserBlizzardError(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Player not found",
        )

    return {
        "summary": _parse_summary(root_tag, player_summary),
        "stats": _parse_stats(root_tag),
    }


def _parse_summary(root_tag: LexborNode, player_summary: dict | None) -> dict:
    """Parse player summary section (username, avatar, endorsement, ranks)"""
    from app.exceptions import ParserParsingError

    player_summary = player_summary or {}

    try:
        profile_div = root_tag.css_first(
            "blz-section.Profile-masthead > div.Profile-player"
        )
        summary_div = profile_div.css_first("div.Profile-player--summaryWrapper")
        progression_div = profile_div.css_first("div.Profile-player--info")

        return {
            "username": summary_div.css_first("h1.Profile-player--name").text(),
            "avatar": (
                player_summary.get("avatar")
                or summary_div.css_first("img.Profile-player--portrait").attributes.get(
                    "src"
                )
            ),
            "namecard": player_summary.get("namecard"),
            "title": get_player_title(
                player_summary.get("title") or _get_title(profile_div)
            ),
            "endorsement": _get_endorsement(progression_div),
            "competitive": _get_competitive_ranks(root_tag, progression_div),
            "last_updated_at": player_summary.get("lastUpdated"),
        }
    except (AttributeError, KeyError, IndexError, TypeError) as error:
        raise ParserParsingError(
            f"Failed to parse player summary: {error!r}"
        ) from error


def _get_title(profile_div: LexborNode) -> str | None:
    """Extract player title from profile div"""
    if not (title_tag := profile_div.css_first("h2.Profile-player--title")):
        return None

    # Special case: "no title" means there is no title
    return title_tag.text() or None


def _get_endorsement(progression_div: LexborNode) -> dict | None:
    """Extract endorsement level and frame"""
    endorsement_span = progression_div.css_first(
        "span.Profile-player--endorsementWrapper"
    )
    if not endorsement_span:
        return None

    endorsement_frame_url = (
        endorsement_span.css_first("img.Profile-playerSummary--endorsement").attributes[
            "src"
        ]
        or ""
    )

    return {
        "level": get_endorsement_value_from_frame(endorsement_frame_url),
        "frame": endorsement_frame_url,
    }


def _get_competitive_ranks(
    root_tag: LexborNode,
    progression_div: LexborNode,
) -> dict | None:
    """Extract competitive ranks for all platforms"""
    competitive_ranks = {
        platform.value: _get_platform_competitive_ranks(
            root_tag,
            progression_div,
            platform,
            platform_class,
        )
        for platform, platform_class in PLATFORMS_DIV_MAPPING.items()
    }

    # If no data for any platform, return None
    return None if not any(competitive_ranks.values()) else competitive_ranks


def _get_platform_competitive_ranks(
    root_tag: LexborNode,
    progression_div: LexborNode,
    platform: PlayerPlatform,
    platform_class: str,
) -> dict | None:
    """Extract competitive ranks for a specific platform"""
    last_season_played = _get_last_season_played(root_tag, platform_class)

    role_wrappers = progression_div.css(
        f"div.Profile-playerSummary--rankWrapper.{platform_class} > div.Profile-playerSummary--roleWrapper",
    )
    if not role_wrappers and not last_season_played:
        return None

    competitive_ranks = {}

    for role_wrapper in role_wrappers:
        role_icon = _get_role_icon(role_wrapper)
        role_key = get_role_key_from_icon(role_icon).value

        rank_tier_icons = role_wrapper.css("img.Profile-playerSummary--rank")
        rank_icon, tier_icon = (
            rank_tier_icons[0].attributes["src"] or "",
            rank_tier_icons[1].attributes["src"] or "",
        )

        competitive_ranks[role_key] = {
            "division": get_division_from_icon(rank_icon).value,
            "tier": get_tier_from_icon(tier_icon),
            "role_icon": role_icon,
            "rank_icon": rank_icon,
            "tier_icon": tier_icon,
        }

    for role in CompetitiveRole:
        if role.value not in competitive_ranks:
            competitive_ranks[role.value] = None

    competitive_ranks["season"] = last_season_played

    return competitive_ranks


def _get_last_season_played(root_tag: LexborNode, platform_class: str) -> int | None:
    """Extract last competitive season played for a platform"""
    if not (profile_section := _get_profile_view_section(root_tag, platform_class)):
        return None

    statistics_section = profile_section.css_first("blz-section.stats.competitive-view")
    last_season_played = statistics_section.attributes.get(
        "data-latestherostatrankseasonow2"
    )
    return int(last_season_played) if last_season_played else None


def _get_profile_view_section(root_tag: LexborNode, platform_class: str) -> LexborNode:
    """Get profile view section for a platform"""
    return root_tag.css_first(f"div.Profile-view.{platform_class}")


def _get_role_icon(role_wrapper: LexborNode) -> str:
    """Extract role icon (format differs between PC and console)"""
    # PC: img tag, Console: svg tag
    if role_div := role_wrapper.css_first("div.Profile-playerSummary--role"):
        return role_div.css_first("img").attributes["src"] or ""

    role_svg = role_wrapper.css_first("svg.Profile-playerSummary--role")
    return role_svg.css_first("use").attributes["xlink:href"] or ""


def _parse_stats(root_tag: LexborNode) -> dict | None:
    """Parse stats for all platforms"""
    stats = {
        platform.value: _parse_platform_stats(root_tag, platform, platform_class)
        for platform, platform_class in PLATFORMS_DIV_MAPPING.items()
    }

    # If no data for any platform, return None
    return None if not any(stats.values()) else stats


def _parse_platform_stats(
    root_tag: LexborNode,
    platform: PlayerPlatform,
    platform_class: str,
) -> dict | None:
    """Parse stats for a specific platform"""
    statistics_section = _get_profile_view_section(root_tag, platform_class)
    gamemodes_infos = {
        gamemode.value: _parse_gamemode_stats(statistics_section, gamemode)
        for gamemode in PlayerGamemode
    }

    # If no data for any gamemode, return None
    return None if not any(gamemodes_infos.values()) else gamemodes_infos


def _parse_gamemode_stats(
    statistics_section: LexborNode,
    gamemode: PlayerGamemode,
) -> dict | None:
    """Parse stats for a specific gamemode"""
    if not statistics_section or not statistics_section.first_child:
        return None

    top_heroes_section = statistics_section.first_child.css_first(
        f"div.{GAMEMODES_DIV_MAPPING[gamemode]}"
    )

    # Check if we have a select element (indicates data exists)
    if not top_heroes_section.css_first("select"):
        return None

    career_stats_section = statistics_section.css_first(
        f"blz-section.{GAMEMODES_DIV_MAPPING[gamemode]}"
    )
    return {
        "heroes_comparisons": _parse_heroes_comparisons(top_heroes_section),
        "career_stats": _parse_career_stats(career_stats_section),
    }


def _parse_heroes_comparisons(top_heroes_section: LexborNode) -> dict:
    """Parse heroes comparisons (top heroes by category)"""
    categories = _get_heroes_options(top_heroes_section)

    heroes_comparisons = {
        string_to_snakecase(
            get_real_category_name(categories[category.attributes["data-category-id"]]),
        ): {
            "label": get_real_category_name(
                categories[category.attributes["data-category-id"]],
            ),
            "values": [
                {
                    # Normally, a valid data-hero-id is present. However, in some
                    # cases — such as when a hero is newly available for testing —
                    # stats may lack an associated ID. In these instances, we fall
                    # back to using the hero's title in lowercase.
                    "hero": (
                        progress_bar_container.first_child.attributes.get(
                            "data-hero-id"
                        )
                        or progress_bar_container.last_child.first_child.text().lower()
                    ),
                    "value": get_computed_stat_value(
                        progress_bar_container.last_child.last_child.text()
                    ),
                }
                for progress_bar in category.iter()
                for progress_bar_container in progress_bar.iter()
                if progress_bar_container.tag == "div"
                and progress_bar_container.first_child is not None
                and progress_bar_container.last_child is not None
                and progress_bar_container.last_child.first_child is not None
                and progress_bar_container.last_child.last_child is not None
            ],
        }
        for category in top_heroes_section.iter()
        if (
            category.attributes["class"] is not None
            and "Profile-progressBars" in category.attributes["class"]
            and category.attributes["data-category-id"] in categories
        )
    }

    for category in CareerHeroesComparisonsCategory:
        # Sometimes, Blizzard exposes the categories without any value
        # In that case, we must assume we have no data at all
        if (
            category.value not in heroes_comparisons
            or not heroes_comparisons[category.value]["values"]
        ):
            heroes_comparisons[category.value] = None

    return heroes_comparisons


def _parse_career_stats(career_stats_section: LexborNode) -> dict:
    """Parse detailed career stats per hero"""
    heroes_options = _get_heroes_options(career_stats_section, key_prefix="option-")

    career_stats = {}

    for hero_container in career_stats_section.iter():
        # Hero container should be span with "stats-container" class
        if hero_container.tag != "span":
            continue

        stats_hero_class = get_stats_hero_class(hero_container.attributes["class"])

        # Sometimes, Blizzard makes some weird things and options don't
        # have any label, so we can't know for sure which hero it is about.
        # So we have to skip this field
        if stats_hero_class not in heroes_options:
            continue

        hero_key = get_hero_keyname(heroes_options[stats_hero_class])

        career_stats[hero_key] = []
        # Hero container children are div with "category" class
        for card_stat in hero_container.iter():
            # Content div should be the only child ("content" class)
            content_div = card_stat.first_child

            # Ensure we have everything we need
            if (
                not content_div
                or not content_div.first_child
                or not content_div.first_child.first_child
            ):
                logger.warning(f"Missing content div for hero {hero_key}")
                continue

            # Label should be the first div within content ("header" class)
            category_label = content_div.first_child.first_child.text()

            career_stats[hero_key].append(
                {
                    "category": string_to_snakecase(category_label),
                    "label": category_label,
                    "stats": [],
                },
            )
            for stat_row in content_div.iter():
                stat_row_class = stat_row.attributes["class"] or ""
                if "stat-item" not in stat_row_class:
                    continue

                if not stat_row.first_child or not stat_row.last_child:
                    logger.warning(f"Missing stat name or value in {stat_row}")
                    continue

                stat_name = stat_row.first_child.text()
                career_stats[hero_key][-1]["stats"].append(
                    {
                        "key": get_plural_stat_key(string_to_snakecase(stat_name)),
                        "label": stat_name,
                        "value": get_computed_stat_value(stat_row.last_child.text()),
                    },
                )

        # For a reason, sometimes the hero is in the dropdown but there
        # is no stat to show. In this case, remove it as if there was
        # no stat at all
        if len(career_stats[hero_key]) == 0:
            del career_stats[hero_key]

    return career_stats


def _get_heroes_options(
    parent_section: LexborNode,
    key_prefix: str = "",
) -> dict[str, str]:
    """Extract hero options from dropdown select element"""
    # Sometimes, pages are not rendered correctly and select can be empty
    if not (
        options := parent_section.css_first("div.Profile-heroSummary--header > select")
    ):
        return {}

    return {
        f"{key_prefix}{option.attributes['value']}": str(option.attributes["option-id"])
        for option in options.iter()
        if option.attributes.get("option-id")
    }


# Filtering functions for API queries


def filter_stats_by_query(
    stats: dict | None,
    platform: PlayerPlatform | None = None,
    gamemode: PlayerGamemode | None = None,
    hero: str | None = None,
) -> dict:
    """
    Filter career stats by query parameters

    Args:
        stats: Raw stats dict from parser
        platform: Optional platform filter
        gamemode: Optional gamemode filter
        hero: Optional hero filter

    Returns:
        Filtered dict of career stats
    """
    filtered_data = stats or {}

    # Determine platform if not specified
    if not platform:
        possible_platforms = [
            platform_key
            for platform_key, platform_data in filtered_data.items()
            if platform_data is not None
        ]
        if possible_platforms:
            # Take the first one of the list, usually there will be only one.
            # If there are two, the PC stats should come first
            platform = possible_platforms[0]
        else:
            return {}

    filtered_data = filtered_data.get(platform) or {}
    if not filtered_data:
        return {}

    filtered_data = filtered_data.get(gamemode) or {}
    if not filtered_data:
        return {}

    filtered_data = filtered_data.get("career_stats") or {}

    return {
        hero_key: statistics
        for hero_key, statistics in filtered_data.items()
        if not hero or hero == hero_key
    }


def filter_all_stats_data(
    stats: dict | None,
    platform: PlayerPlatform | None = None,
    gamemode: PlayerGamemode | None = None,
) -> dict:
    """
    Filter all stats data by platform and/or gamemode

    Args:
        stats: Raw stats dict from parser
        platform: Optional platform filter
        gamemode: Optional gamemode filter

    Returns:
        Filtered stats dict (may set platforms/gamemodes to None if not matching)
    """
    stats_data = stats or {}

    # Return early if no filters
    if not platform and not gamemode:
        return stats_data

    filtered_data = {}

    for platform_key, platform_data in stats_data.items():
        if platform and platform_key != platform:
            filtered_data[platform_key] = None
            continue

        if platform_data is None:
            filtered_data[platform_key] = None
            continue

        if gamemode is None:
            filtered_data[platform_key] = platform_data
            continue

        filtered_data[platform_key] = {
            gamemode_key: (gamemode_data if gamemode_key == gamemode else None)
            for gamemode_key, gamemode_data in platform_data.items()
        }

    return filtered_data


async def parse_player_profile(
    client: BlizzardClient,
    player_id: str,
    player_summary: dict | None = None,
) -> dict:
    """
    High-level function to fetch and parse player profile

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (Blizzard ID format)
        player_summary: Optional player summary from search endpoint

    Returns:
        Dict with "summary" and "stats" keys
    """
    html = await fetch_player_html(client, player_id)
    return parse_player_profile_html(html, player_summary)
