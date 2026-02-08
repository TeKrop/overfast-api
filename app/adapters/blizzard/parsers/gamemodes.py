"""Stateless parser functions for gamemodes data"""

from app.adapters.csv import CSVReader
from app.config import settings


def get_static_url_gamemodes(key: str, extension: str) -> str:
    """Get URL for a gamemode static file"""
    return f"{settings.app_base_url}/static/gamemodes/{key}.{extension}"


def parse_gamemodes_csv() -> list[dict]:
    """
    Parse gamemodes list from CSV file
    
    Returns:
        List of gamemode dicts with keys: key, name, icon, description, screenshot
    """
    csv_reader = CSVReader()
    csv_data = csv_reader.read_csv_file("gamemodes")
    
    return [
        {
            "key": gamemode["key"],
            "name": gamemode["name"],
            "icon": get_static_url_gamemodes(f"{gamemode['key']}-icon", "svg"),
            "description": gamemode["description"],
            "screenshot": get_static_url_gamemodes(gamemode["key"], "avif"),
        }
        for gamemode in csv_data
    ]


def parse_gamemodes() -> list[dict]:
    """
    High-level function to parse gamemodes
    
    Returns:
        List of gamemode dicts
    """
    return parse_gamemodes_csv()
