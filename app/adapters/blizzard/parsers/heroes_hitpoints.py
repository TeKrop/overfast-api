"""Stateless parser functions for heroes hitpoints data (HP, armor, shields) from CSV"""

from app.adapters.csv import CSVReader

HITPOINTS_KEYS = {"health", "armor", "shields"}


def parse_heroes_hitpoints() -> dict[str, dict]:
    """Parse heroes hitpoints (health/armor/shields) from the heroes CSV file.

    Returns:
        Dict mapping hero key to hitpoints data.
        Example: {"ana": {"hitpoints": {"health": 200, "armor": 0, "shields": 0, "total": 200}}}
    """
    csv_reader = CSVReader()
    csv_data = csv_reader.read_csv_file("heroes")

    return {row["key"]: {"hitpoints": _get_hitpoints(row)} for row in csv_data}


def _get_hitpoints(row: dict) -> dict:
    """Extract hitpoints data from a hero CSV row."""
    hitpoints = {hp_key: int(row[hp_key]) for hp_key in HITPOINTS_KEYS}
    hitpoints["total"] = sum(hitpoints.values())
    return hitpoints
