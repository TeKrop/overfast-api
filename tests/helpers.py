import json
from pathlib import Path

from app.config import settings


def read_html_file(filepath: str) -> str | None:
    """Helper method for retrieving fixture HTML file data"""
    html_file_object = Path(f"{settings.test_fixtures_root_path}/html/{filepath}")
    if not html_file_object.is_file():
        return None  # pragma: no cover

    with html_file_object.open(encoding="utf-8") as html_file:
        return html_file.read()


def read_json_file(filepath: str) -> dict | list | None:
    """Helper method for retrieving fixture JSON file data"""
    with Path(f"{settings.test_fixtures_root_path}/json/{filepath}").open(
        encoding="utf-8",
    ) as json_file:
        return json.load(json_file)


# List of players used for testing
players_ids = [
    "KIRIKO-12460",  # Console player
    "TeKrop-2217",  # Classic profile
    "JohnV1-1190",  # Player without any title ingame
]

# Non-existent player ID used for testing
unknown_player_id = "Unknown-1234"
