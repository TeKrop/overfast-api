"""Parser Helpers module"""
import re
import unicodedata
from typing import Optional

from overfastapi.config import BLIZZARD_HOST


def get_background_url_from_style(style: str) -> Optional[str]:
    """Extracts the URL of a background-image CSS rule from an
    HTML style attribute. Returns None if not found.
    """
    url = re.findall(r"background-image: ?url\((.*)\)", style)
    return url[0].strip() or None if url else None


def get_full_url(url: str) -> str:
    """Get full URL from extracted URL. If URL begins with /, we use the
    blizzard host to get the full URL"""
    return f"{BLIZZARD_HOST}{url}" if url.startswith("/") else url


def remove_accents(input_str: str) -> str:
    """Removes accents from a string and return the resulting string"""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def string_to_snakecase(input_str: str) -> str:
    """Returns a string transformed in snakecase format"""
    cleaned_str = remove_accents(input_str).replace("- ", "")
    return (
        re.sub(r"(?<=[a-z])(?=[A-Z])|[^a-zA-Z0-9]", "_", cleaned_str).strip("_").lower()
    )


def get_hero_keyname(input_str: str) -> str:
    """Returns Overwatch hero keyname using its fullname.
    Example : ("Soldier: 76" -> "soldier-76")
    """
    input_str = input_str.replace(".", "").replace(":", "")
    return string_to_snakecase(input_str).replace("_", "-")


def get_computed_stat_value(input_str: str) -> str | float | int:
    """Get computed value from player statistics : convert duration representations
    into seconds (int), percentages into int, cast integer and float strings into
    int and float respectively.
    """

    # Duration format in hour:min:sec => seconds
    result = re.match(r"^([0-9]+[,]?[0-9]*?):([0-9]+):([0-9]+)$", input_str)
    if result:
        return (
            int(result.group(1).replace(",", "")) * 3600
            + int(result.group(2)) * 60
            + int(result.group(3))
        )

    # Duration format in min:sec => seconds
    result = re.match(r"^([0-9]+):([0-9]+)$", input_str)
    if result:
        return int(result.group(1)) * 60 + int(result.group(2))

    # Int format
    if re.match(r"^[0-9]+%?$", input_str):
        return int(input_str.replace("%", ""))

    # Float format
    if re.match(r"^[0-9]+\.[0-9]+?$", input_str):
        return float(input_str)

    # Zero time fought with a character
    if input_str == "--":
        return 0

    # Default value for anything else
    return input_str
