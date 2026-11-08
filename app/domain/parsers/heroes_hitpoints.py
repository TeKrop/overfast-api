"""Stateless parser functions for heroes hitpoints data (HP, armor, shields) from CSV"""

from typing import Any

from app.domain.utils.csv_reader import read_csv_file

HITPOINTS_KEYS = {"health", "armor", "shields"}


def parse_heroes_hitpoints() -> dict[str, dict[str, Any]]:
    """Parse heroes hitpoints (health/armor/shields) from the heroes CSV file.

    Returns:
        Dict mapping hero key to hitpoints data.
        Example: {"ana": {"hitpoints": {"health": 200, "armor": 0, "shields": 0, "total": 200}}}
    """
    csv_data = read_csv_file("heroes")

    return {row["key"]: {"hitpoints": _get_hitpoints(row)} for row in csv_data}


def _get_hitpoints(row: dict[str, Any]) -> dict[str, Any]:
    """Extract hitpoints data from a hero CSV row."""
    hitpoints = {hp_key: int(row[hp_key]) for hp_key in HITPOINTS_KEYS}
    hitpoints["total"] = sum(hitpoints.values())
    return hitpoints
