"""Set of enumerations of generic data displayed in the API :
heroes, gamemodes, etc.

"""
from enum import StrEnum

from app.common.helpers import read_csv_data_file

# Dynamically create the HeroKey enum by using the CSV File
heroes_data = read_csv_data_file("heroes.csv")
HeroKey = StrEnum(
    "HeroKey",
    {
        hero_data["key"].upper().replace("-", "_"): hero_data["key"]
        for hero_data in heroes_data
    },
)
HeroKey.__doc__ = "Hero keys used to identify Overwatch heroes in general"


class CareerStatCategory(StrEnum):
    """Categories of general statistics displayed in the players API"""

    ASSISTS = "assists"
    AVERAGE = "average"
    BEST = "best"
    COMBAT = "combat"
    GAME = "game"
    HERO_SPECIFIC = "hero_specific"
    MATCH_AWARDS = "match_awards"
    MISCELLANEOUS = "miscellaneous"


class CareerHeroesComparisonsCategory(StrEnum):
    """Categories of heroes stats in player comparisons"""

    TIME_PLAYED = "time_played"
    GAMES_WON = "games_won"
    WEAPON_ACCURACY = "weapon_accuracy"
    WIN_PERCENTAGE = "win_percentage"
    ELIMINATIONS_PER_LIFE = "eliminations_per_life"
    CRITICAL_HIT_ACCURACY = "critical_hit_accuracy"
    MULTIKILL_BEST = "multikill_best"
    OBJECTIVE_KILLS = "objective_kills"


class RouteTag(StrEnum):
    """Tags used to classify API routes"""

    HEROES = "🦸 Heroes"
    GAMEMODES = "🎲 Gamemodes"
    MAPS = "🗺️ Maps"
    PLAYERS = "🎮 Players"


# Dynamically create the HeroKeyCareerFilter by using the existing
# HeroKey enum and just adding the "all-heroes" option
HeroKeyCareerFilter = StrEnum(
    "HeroKeyCareerFilter",
    {
        "ALL_HEROES": "all-heroes",
        **{hero_key.name: hero_key.value for hero_key in HeroKey},
    },
)
HeroKeyCareerFilter.__doc__ = "Hero keys filter for career statistics endpoint"


class MediaType(StrEnum):
    """Media types for heroes pages"""

    COMIC = "comic"
    SHORT_STORY = "short-story"
    VIDEO = "video"


class Role(StrEnum):
    """Overwatch heroes roles"""

    DAMAGE = "damage"
    SUPPORT = "support"
    TANK = "tank"


class PlayerGamemode(StrEnum):
    """Gamemodes associated with players statistics"""

    QUICKPLAY = "quickplay"
    COMPETITIVE = "competitive"


class PlayerPlatform(StrEnum):
    """Players platforms"""

    CONSOLE = "console"
    PC = "pc"


class PlayerPrivacy(StrEnum):
    """Players career privacy"""

    PUBLIC = "public"
    PRIVATE = "private"


class CompetitiveDivision(StrEnum):
    """Competitive division of a rank"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"


class Locale(StrEnum):
    """Locales supported by Blizzard"""

    GERMAN = "de-de"
    ENGLISH_EU = "en-gb"
    ENGLISH_US = "en-us"
    SPANISH_EU = "es-es"
    SPANISH_LATIN = "es-mx"
    FRENCH = "fr-fr"
    ITALIANO = "it-it"
    JAPANESE = "ja-jp"
    KOREAN = "ko-kr"
    POLISH = "pl-pl"
    PORTUGUESE_BRAZIL = "pt-br"
    RUSSIAN = "ru-ru"
    CHINESE_TAIWAN = "zh-tw"


# Dynamically create the MapGamemode enum by using the CSV File
gamemodes_data = read_csv_data_file("gamemodes.csv")
MapGamemode = StrEnum(
    "MapGamemode",
    {
        gamemode["key"].upper().replace("-", "_"): gamemode["key"]
        for gamemode in gamemodes_data
    },
)
MapGamemode.__doc__ = "Maps gamemodes keys"


class SearchDataType(StrEnum):
    NAMECARD = "namecard"
    PORTRAIT = "portrait"
    TITLE = "title"
