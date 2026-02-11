from enum import StrEnum

from app.helpers import read_csv_data_file


class MediaType(StrEnum):
    """Media types for heroes pages"""

    COMIC = "comic"
    SHORT_STORY = "short-story"
    VIDEO = "video"


# Dynamically create the HeroKey enum by using the CSV File
heroes_data = read_csv_data_file("heroes")
HeroKey = StrEnum(
    "HeroKey",
    {
        hero_data["key"].upper().replace("-", "_"): hero_data["key"]
        for hero_data in heroes_data
    },
)
HeroKey.__doc__ = "Hero keys used to identify Overwatch heroes in general"


class HeroGamemode(StrEnum):
    """Available gamemodes for heroes"""

    QUICKPLAY = "quickplay"
    STADIUM = "stadium"
