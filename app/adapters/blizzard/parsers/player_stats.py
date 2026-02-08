"""Stateless parser for player stats summary with aggregations

This module computes aggregated player statistics with:
- Heroes stats (per hero with winrate, KDA, averages)
- Roles stats (aggregated by role)
- General stats (overall aggregation)
"""

from collections import defaultdict
from copy import deepcopy
from typing import TYPE_CHECKING

from app.adapters.blizzard.parsers.player_profile import (
    parse_player_profile,
    parse_player_profile_html,
)
from app.players.enums import HeroKey, PlayerGamemode, PlayerPlatform
from app.players.helpers import get_hero_role, get_plural_stat_key
from app.roles.enums import Role

if TYPE_CHECKING:
    from app.adapters.blizzard.client import BlizzardClient

# Stat names for aggregation
GENERIC_STATS_NAMES = [
    "games_played",
    "games_won",
    "games_lost",
    "time_played",
]
TOTAL_STATS_NAMES = [
    "eliminations",
    "assists",
    "deaths",
    "damage",
    "healing",
]

# Placeholder structure for stats
STATS_PLACEHOLDER = {
    "games_played": 0,
    "games_won": 0,
    "games_lost": 0,
    "time_played": 0,
    "winrate": 0,
    "kda": 0,
    "total": {
        "eliminations": 0,
        "assists": 0,
        "deaths": 0,
        "damage": 0,
        "healing": 0,
    },
}


def extract_heroes_stats_from_profile(profile_stats: dict) -> dict:
    """
    Extract and compute heroes stats from profile data

    Args:
        profile_stats: Stats dict from profile parser

    Returns:
        Dict mapping hero_key to platform/gamemode stats
    """
    if not profile_stats:
        return {}

    # Filter only platforms with stats
    raw_heroes_stats = {
        platform: platform_stats
        for platform, platform_stats in profile_stats.items()
        if platform_stats
    }

    # Compute the data
    heroes_stats = _compute_heroes_stats(raw_heroes_stats)

    # Only return heroes for which we have stats
    return {
        hero_key: hero_stat for hero_key, hero_stat in heroes_stats.items() if hero_stat
    }


def _compute_heroes_stats(raw_heroes_stats: dict) -> dict:
    """Compute heroes stats for every gamemode and platform"""
    heroes_stats = {hero_key: defaultdict(dict) for hero_key in HeroKey}

    for platform, platform_stats in raw_heroes_stats.items():
        platform_gamemodes_stats = {
            gamemode: gamemode_stats
            for gamemode, gamemode_stats in platform_stats.items()
            if gamemode_stats
        }

        for gamemode, gamemode_stats in platform_gamemodes_stats.items():
            career_stats = {
                hero_key: hero_stats
                for hero_key, hero_stats in gamemode_stats["career_stats"].items()
                if hero_stats and hero_key != "all-heroes"
            }

            for hero_key, hero_stats in career_stats.items():
                heroes_stats[hero_key][platform][gamemode] = _compute_hero_stats(
                    hero_stats
                )

    return heroes_stats


def _compute_hero_stats(hero_stats: list[dict]) -> dict:
    """Compute a single hero statistics"""
    game_stats = _get_category_stats("game", hero_stats)
    games_played = _get_stat_value("games_played", game_stats)
    time_played = _get_stat_value("time_played", game_stats)
    games_lost = _get_stat_value("games_lost", game_stats)

    # Sometimes, games lost are negative on Blizzard page. To not
    # disturb too much the winrate, we put a value for 50% winrate
    games_lost = round(games_played / 2) if games_lost < 0 else games_lost

    # Calculate games won (sometimes Blizzard exposes "Games Won" multiple times
    # with different values, but games_lost is consistent)
    games_won = games_played - games_lost

    # Make sure it's not negative
    games_won = max(games_won, 0)

    combat_stats = _get_category_stats("combat", hero_stats)
    eliminations = _get_stat_value("eliminations", combat_stats)
    deaths = _get_stat_value("deaths", combat_stats)
    damage = _get_stat_value("all_damage_done", combat_stats)

    assists_stats = _get_category_stats("assists", hero_stats)
    assists = _get_stat_value("offensive_assists", assists_stats)
    healing = _get_stat_value("healing_done", assists_stats)

    return {
        "games_played": games_played,
        "games_won": games_won,
        "games_lost": games_lost,
        "time_played": time_played,
        "total": {
            "eliminations": eliminations,
            "assists": assists,
            "deaths": deaths,
            "damage": damage,
            "healing": healing,
        },
    }


def _get_category_stats(category: str, hero_stats: list[dict]) -> list[dict]:
    """Extract stats for a specific category"""
    category_stats = filter(lambda x: x["category"] == category, hero_stats)
    try:
        return next(category_stats)["stats"]
    except StopIteration:
        return []


def _get_stat_value(stat_name: str, stats_list: list[dict]) -> int | float:
    """Extract a specific stat value from stats list"""
    stat_value = filter(
        lambda x: get_plural_stat_key(x["key"]) == stat_name,
        stats_list,
    )
    try:
        return next(stat_value)["value"]
    except StopIteration:
        return 0


def compute_heroes_data(
    heroes_stats: dict,
    gamemodes: list[PlayerGamemode],
    platforms: list[PlayerPlatform],
) -> dict | None:
    """
    Compute heroes data filtered by gamemodes and platforms

    Args:
        heroes_stats: Heroes stats dict from extract_heroes_stats_from_profile
        gamemodes: List of gamemodes to include
        platforms: List of platforms to include

    Returns:
        Computed heroes stats with winrate, KDA, averages
    """
    if not heroes_stats:
        return None

    # Init heroes data by aggregating across platforms/gamemodes
    computed_heroes_stats = {}

    for hero_key, hero_stats in heroes_stats.items():
        computed_heroes_stats[hero_key] = deepcopy(STATS_PLACEHOLDER)

        # Retrieve raw data from heroes
        hero_platforms = {platform for platform in platforms if platform in hero_stats}
        for platform in hero_platforms:
            hero_platform_gamemodes = {
                gamemode for gamemode in gamemodes if gamemode in hero_stats[platform]
            }

            for gamemode in hero_platform_gamemodes:
                for stat_name in GENERIC_STATS_NAMES:
                    computed_heroes_stats[hero_key][stat_name] += hero_stats[platform][
                        gamemode
                    ][stat_name]
                for stat_name in TOTAL_STATS_NAMES:
                    computed_heroes_stats[hero_key]["total"][stat_name] += hero_stats[
                        platform
                    ][gamemode]["total"][stat_name]

    # Calculate special values (winrate, kda, averages)
    for hero_key, hero_stats in computed_heroes_stats.items():
        # Ignore computation for heroes without stats
        if hero_stats["time_played"] <= 0:
            continue

        computed_heroes_stats[hero_key]["winrate"] = _calculate_winrate(hero_stats)
        computed_heroes_stats[hero_key]["kda"] = _calculate_kda(hero_stats)
        computed_heroes_stats[hero_key]["average"] = _calculate_averages(hero_stats)

    # Only return the heroes for which we have stats
    return {
        hero_key: hero_stats
        for hero_key, hero_stats in computed_heroes_stats.items()
        if hero_stats["time_played"] > 0
    }


def compute_roles_stats(heroes_stats: dict) -> dict:
    """
    Aggregate heroes stats by role

    Args:
        heroes_stats: Computed heroes stats

    Returns:
        Role-aggregated stats
    """
    # Initialize stats
    roles_stats = {role_key: deepcopy(STATS_PLACEHOLDER) for role_key in Role}

    # Retrieve raw data from heroes
    for hero_key, hero_stats in heroes_stats.items():
        hero_role = get_hero_role(hero_key)
        for stat_name in GENERIC_STATS_NAMES:
            roles_stats[hero_role][stat_name] += hero_stats[stat_name]
        for stat_name in TOTAL_STATS_NAMES:
            roles_stats[hero_role]["total"][stat_name] += hero_stats["total"][stat_name]

    # Calculate special values (winrate, kda, averages)
    for role_key, role_stat in roles_stats.items():
        roles_stats[role_key]["winrate"] = _calculate_winrate(role_stat)
        roles_stats[role_key]["kda"] = _calculate_kda(role_stat)
        roles_stats[role_key]["average"] = _calculate_averages(role_stat)

    # Only return the roles for which the player has played
    return {
        role_key: role_stat
        for role_key, role_stat in roles_stats.items()
        if isinstance(role_stat["time_played"], int) and role_stat["time_played"] > 0
    }


def compute_general_stats(roles_stats: dict) -> dict:
    """
    Aggregate role stats into general stats

    Args:
        roles_stats: Role-aggregated stats

    Returns:
        General (overall) stats
    """
    general_stats = deepcopy(STATS_PLACEHOLDER)

    # Retrieve raw data from roles
    for role_stat in roles_stats.values():
        for stat_name in GENERIC_STATS_NAMES:
            general_stats[stat_name] += role_stat[stat_name]
        for stat_name in TOTAL_STATS_NAMES:
            general_stats["total"][stat_name] += role_stat["total"][stat_name]

    # Calculate special values (winrate, kda, averages)
    general_stats["winrate"] = _calculate_winrate(general_stats)
    general_stats["kda"] = _calculate_kda(general_stats)
    general_stats["average"] = _calculate_averages(general_stats)

    return general_stats


def _calculate_winrate(stat: dict) -> float:
    """Calculate winrate percentage"""
    games_won = stat.get("games_won") or 0
    games_played = stat.get("games_played") or 0
    return 0 if games_played <= 0 else round((games_won / games_played) * 100, 2)


def _calculate_kda(stat: dict) -> float:
    """Calculate KDA ratio"""
    eliminations = stat["total"]["eliminations"] or 0
    assists = stat["total"]["assists"] or 0
    deaths = stat["total"]["deaths"] or 0
    return round((eliminations + assists) / deaths, 2) if deaths > 0 else 0


def _calculate_averages(stat: dict) -> dict:
    """Calculate per-10-minutes averages"""
    ten_minutes_played = stat["time_played"] / 600
    return {
        key: (
            round(stat["total"][key] / ten_minutes_played, 2)
            if ten_minutes_played > 0
            else 0
        )
        for key in stat["total"]
    }


def parse_player_stats_summary_from_html(
    html: str,
    player_summary: dict | None = None,
    gamemode: PlayerGamemode | None = None,
    platform: PlayerPlatform | None = None,
) -> dict:
    """
    Parse player stats summary from HTML (for Player Cache usage)

    Args:
        html: Player profile HTML
        player_summary: Optional player summary from search endpoint
        gamemode: Optional gamemode filter
        platform: Optional platform filter

    Returns:
        Dict with "general", "roles", and "heroes" stats
    """
    # Determine filters
    gamemodes = [gamemode] if gamemode else list(PlayerGamemode)
    platforms = [platform] if platform else list(PlayerPlatform)

    # Parse HTML to get profile data
    profile_data = parse_player_profile_html(html, player_summary)

    # Extract heroes stats
    heroes_stats = extract_heroes_stats_from_profile(profile_data.get("stats") or {})

    # Compute heroes data with filters
    heroes_data = compute_heroes_data(heroes_stats, gamemodes, platforms)
    if not heroes_data:
        return {}

    # Compute roles and general stats
    roles_stats = compute_roles_stats(heroes_data)
    general_stats = compute_general_stats(roles_stats)

    return {
        "general": general_stats,
        "roles": roles_stats,
        "heroes": heroes_data,
    }


async def parse_player_stats_summary(
    client: BlizzardClient,
    player_id: str,
    player_summary: dict | None = None,
    gamemode: PlayerGamemode | None = None,
    platform: PlayerPlatform | None = None,
) -> dict:
    """
    High-level function to parse player stats summary

    Args:
        client: Blizzard HTTP client
        player_id: Player ID (Blizzard ID format)
        player_summary: Optional player summary from search endpoint
        gamemode: Optional gamemode filter
        platform: Optional platform filter

    Returns:
        Dict with "general", "roles", and "heroes" stats
    """
    # Determine filters
    gamemodes = [gamemode] if gamemode else list(PlayerGamemode)
    platforms = [platform] if platform else list(PlayerPlatform)

    # Fetch full profile
    profile_data = await parse_player_profile(client, player_id, player_summary)

    # Extract heroes stats
    heroes_stats = extract_heroes_stats_from_profile(profile_data.get("stats") or {})

    # Compute heroes data with filters
    heroes_data = compute_heroes_data(heroes_stats, gamemodes, platforms)
    if not heroes_data:
        return {}

    # Compute roles and general stats
    roles_stats = compute_roles_stats(heroes_data)
    general_stats = compute_general_stats(roles_stats)

    return {
        "general": general_stats,
        "roles": roles_stats,
        "heroes": heroes_data,
    }
