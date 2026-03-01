"""Domain helper utilities"""

from functools import cache

from app.domain.utils.csv_reader import CSVReader


@cache
def get_hero_name(hero_key: str) -> str:
    """Return the display name for a hero key, falling back to the key itself."""
    heroes_data = CSVReader.read_csv_file("heroes")
    return next(
        (
            hero_data["name"]
            for hero_data in heroes_data
            if hero_data["key"] == hero_key
        ),
        hero_key,
    )


@cache
def key_to_label(key: str) -> str:
    """Transform a snake_case key into a human-readable Title Case label."""
    return " ".join(s.capitalize() for s in key.split("_"))
