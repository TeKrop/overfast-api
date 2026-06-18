"""Stateless parser functions for maps data"""

from app.config import settings
from app.domain.utils.csv_reader import read_csv_file


def get_static_url_maps(key: str, extension: str = "jpg") -> str:
    """Get URL for a map screenshot"""
    return f"{settings.app_base_url}/static/maps/{key}.{extension}"


def parse_maps_csv() -> list[dict]:
    """
    Parse maps list from CSV file

    Returns:
        List of map dicts with keys: key, name, screenshot, gamemodes, location, country_code
    """
    csv_data = read_csv_file("maps")

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
