"""Parser Helpers module"""
import re
import unicodedata

from overfastapi.common.enums import CompetitiveDivision, Role
from overfastapi.config import BLIZZARD_HOST


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
    if re.match(r"^[-]?[0-9]+%?$", input_str):
        return int(input_str.replace("%", ""))

    # Float format
    if re.match(r"^[-]?[0-9]+\.[0-9]+?$", input_str):
        return float(input_str)

    # Zero time fought with a character
    if input_str == "--":
        return 0

    # Default value for anything else
    return input_str


def get_division_from_rank_icon(rank_url: str) -> CompetitiveDivision:
    division_name = rank_url.split("/")[-1].split("-")[0]
    return CompetitiveDivision(division_name[:-4].lower())


def get_endorsement_value_from_frame(frame_url: str) -> int:
    """Extracts the endorsement level from the frame URL. 0 if not found."""
    try:
        return int(frame_url.split("/")[-1].split("-")[0])
    except ValueError:
        return 0


def get_full_url(url: str) -> str:
    """Get full URL from extracted URL. If URL begins with /, we use the
    blizzard host to get the full URL"""
    return f"{BLIZZARD_HOST}{url}" if url.startswith("/") else url


def get_hero_keyname(input_str: str) -> str:
    """Returns Overwatch hero keyname using its fullname.
    Example : ("Soldier: 76" -> "soldier-76")
    """
    input_str = input_str.replace(".", "").replace(":", "")
    return string_to_snakecase(input_str).replace("_", "-")


def get_role_key_from_icon(icon_url: str) -> Role:
    """Extract role key from the role icon."""
    icon_role_key = icon_url.split("/")[-1].split("-")[0]
    return Role.DAMAGE if icon_role_key == "offense" else Role(icon_role_key)


def get_stats_hero_class(hero_classes: list[str]) -> str:
    """Extract the specific classname from the classes list for a given hero."""
    return [classname for classname in hero_classes if classname.startswith("option-")][
        0
    ]


def get_tier_from_rank_icon(rank_url: str) -> int:
    """Extracts the rank tier from the rank URL. 0 if not found."""
    try:
        return int(rank_url.split("/")[-1].split("-")[1])
    except (IndexError, ValueError):
        return 0


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
