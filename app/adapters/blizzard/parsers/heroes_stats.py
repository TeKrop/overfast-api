"""Stateless parser functions for heroes stats data (HP, armor, shields)"""

from app.adapters.csv import CSVReader

HITPOINTS_KEYS = {"health", "armor", "shields"}


def parse_heroes_stats_csv() -> dict[str, dict]:
    """
    Parse heroes stats (hitpoints) from CSV file

    Returns:
        Dict mapping hero key to stats dict with hitpoints data
        Example: {"ana": {"hitpoints": {"health": 200, "armor": 0, "shields": 0, "total": 200}}}
    """
    csv_reader = CSVReader()
    csv_data = csv_reader.read_csv_file("heroes")

    return {
        hero_stats["key"]: {"hitpoints": _get_hitpoints(hero_stats)}
        for hero_stats in csv_data
    }


def _get_hitpoints(hero_stats: dict) -> dict:
    """Extract hitpoints data from hero CSV row"""
    hitpoints = {hp_key: int(hero_stats[hp_key]) for hp_key in HITPOINTS_KEYS}
    hitpoints["total"] = sum(hitpoints.values())
    return hitpoints


def parse_heroes_stats() -> dict[str, dict]:
    """
    High-level function to parse heroes stats

    Returns:
        Dict mapping hero key to stats
    """
    return parse_heroes_stats_csv()
