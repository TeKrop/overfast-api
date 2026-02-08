"""Stateless parser functions for maps data"""

from app.adapters.csv import CSVReader
from app.config import settings


def get_static_url_maps(key: str, extension: str = "jpg") -> str:
    """Get URL for a map screenshot"""
    return f"{settings.app_base_url}/static/maps/{key}.{extension}"


def parse_maps_csv() -> list[dict]:
    """
    Parse maps list from CSV file

    Returns:
        List of map dicts with keys: key, name, screenshot, gamemodes, location, country_code
    """
    csv_reader = CSVReader()
    csv_data = csv_reader.read_csv_file("maps")

    return [
        {
            "key": map_dict["key"],
            "name": map_dict["name"],
            "screenshot": get_static_url_maps(map_dict["key"]),
            "gamemodes": map_dict["gamemodes"].split(","),
            "location": map_dict["location"],
            "country_code": map_dict.get("country_code") or None,
        }
        for map_dict in csv_data
    ]


def filter_maps_by_gamemode(maps: list[dict], gamemode: str | None) -> list[dict]:
    """Filter maps by gamemode"""
    if not gamemode:
        return maps
    return [map_dict for map_dict in maps if gamemode in map_dict["gamemodes"]]


def parse_maps(gamemode: str | None = None) -> list[dict]:
    """
    High-level function to parse and filter maps

    Args:
        gamemode: Optional gamemode filter

    Returns:
        List of map dicts, optionally filtered by gamemode
    """
    maps = parse_maps_csv()
    return filter_maps_by_gamemode(maps, gamemode)
