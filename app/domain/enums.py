"""Consolidated domain enums for OverFast API"""

from enum import StrEnum

from app.adapters.csv import CSVReader


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


class Role(StrEnum):
    """Overwatch heroes roles"""

    DAMAGE = "damage"
    SUPPORT = "support"
    TANK = "tank"


class BackgroundImageSize(StrEnum):
    """Responsive breakpoint sizes for hero background images"""

    MIN = "min"
    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL_PLUS = "xl+"


class MediaType(StrEnum):
    """Media types for heroes pages"""

    COMIC = "comic"
    SHORT_STORY = "short-story"
    VIDEO = "video"


# Dynamically create the HeroKey enum by using the CSV File
heroes_data = CSVReader.read_csv_file("heroes")
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


# Dynamically create the MapKey enum by using the CSV File
maps_data = CSVReader.read_csv_file("maps")
MapKey = StrEnum(
    "MapKey",
    {
        map_data["key"].upper().replace("-", "_"): map_data["key"]
        for map_data in maps_data
    },
)
MapKey.__doc__ = "Map keys used to identify Overwatch maps in general"


# Dynamically create the MapGamemode enum by using the CSV File
gamemodes_data = CSVReader.read_csv_file("gamemodes")
MapGamemode = StrEnum(
    "MapGamemode",
    {
        gamemode["key"].upper().replace("-", "_"): gamemode["key"]
        for gamemode in gamemodes_data
    },
)
MapGamemode.__doc__ = "Maps gamemodes keys"


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
    WIN_PERCENTAGE = "win_percentage"
    WEAPON_ACCURACY_BEST_IN_GAME = "weapon_accuracy_best_in_game"
    ELIMINATIONS_PER_LIFE = "eliminations_per_life"
    KILL_STREAK_BEST = "kill_streak_best"
    MULTIKILL_BEST = "multikill_best"
    ELIMINATIONS_AVG_PER_10_MIN = "eliminations_avg_per_10_min"
    DEATHS_AVG_PER_10_MIN = "deaths_avg_per_10_min"
    FINAL_BLOWS_AVG_PER_10_MIN = "final_blows_avg_per_10_min"
    SOLO_KILLS_AVG_PER_10_MIN = "solo_kills_avg_per_10_min"
    OBJECTIVE_KILLS_AVG_PER_10_MIN = "objective_kills_avg_per_10_min"
    OBJECTIVE_TIME_AVG_PER_10_MIN = "objective_time_avg_per_10_min"
    HERO_DAMAGE_DONE_AVG_PER_10_MIN = "hero_damage_done_avg_per_10_min"
    HEALING_DONE_AVG_PER_10_MIN = "healing_done_avg_per_10_min"


# Dynamically create the HeroKeyCareerFilter by using the existing
# HeroKey enum and just adding the "all-heroes" option
HeroKeyCareerFilter = StrEnum(
    "HeroKeyCareerFilter",
    {
        "ALL_HEROES": "all-heroes",
        **{hero_key.name: hero_key.value for hero_key in HeroKey},  # ty: ignore[unresolved-attribute]
    },
)
HeroKeyCareerFilter.__doc__ = "Hero keys filter for career statistics endpoint"


# Dynamically create the CompetitiveRole enum by using the existing
# Role enum and just adding the "open" option for Open Queue
CompetitiveRole = StrEnum(
    "CompetitiveRole",
    {
        **{role.name: role.value for role in Role},
        "OPEN": "open",
    },
)
CompetitiveRole.__doc__ = "Competitive roles for ranks in stats summary"


class PlayerGamemode(StrEnum):
    """Gamemodes associated with players statistics"""

    QUICKPLAY = "quickplay"
    COMPETITIVE = "competitive"


class PlayerPlatform(StrEnum):
    """Players platforms"""

    CONSOLE = "console"
    PC = "pc"


class CompetitiveDivision(StrEnum):
    """Competitive division of a rank"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    ULTIMATE = "ultimate"


class PlayerRegion(StrEnum):
    EUROPE = "europe"
    AMERICAS = "americas"
    ASIA = "asia"


# ULTIMATE competitive division doesn't exists in hero stats endpoint
CompetitiveDivisionFilter = StrEnum(
    "CompetitiveDivisionFilter",
    {tier.name: tier.value for tier in CompetitiveDivision if tier.name != "ULTIMATE"},
)
CompetitiveDivisionFilter.__doc__ = (
    "Competitive divisions ('grandmaster' includes 'champion')"
)
