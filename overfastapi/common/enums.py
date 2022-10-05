"""Set of enumerations of generic data displayed in the API :
heroes, maps gamemodes, achievements categories, platforms, player roles, etc.

"""
from enum import Enum


class StrEnum(str, Enum):
    """Generic Enum which will be casted easily as a string"""


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


class HeroKey(StrEnum):
    """Hero keys used to identify Overwatch heroes in general"""

    ANA = "ana"
    ASHE = "ashe"
    BAPTISTE = "baptiste"
    BASTION = "bastion"
    BRIGITTE = "brigitte"
    CASSIDY = "cassidy"
    DVA = "dva"
    DOOMFIST = "doomfist"
    ECHO = "echo"
    GENJI = "genji"
    HANZO = "hanzo"
    JUNKER_QUEEN = "junker-queen"
    JUNKRAT = "junkrat"
    KIRIKO = "kiriko"
    LUCIO = "lucio"
    MEI = "mei"
    MERCY = "mercy"
    MOIRA = "moira"
    ORISA = "orisa"
    PHARAH = "pharah"
    REAPER = "reaper"
    REINHARDT = "reinhardt"
    ROADHOG = "roadhog"
    SIGMA = "sigma"
    SOJOURN = "sojourn"
    SOLDIER_76 = "soldier-76"
    SOMBRA = "sombra"
    SYMMETRA = "symmetra"
    TORBJORN = "torbjorn"
    TRACER = "tracer"
    WIDOWMAKER = "widowmaker"
    WINSTON = "winston"
    WRECKING_BALL = "wrecking-ball"
    ZARYA = "zarya"
    ZENYATTA = "zenyatta"


class MediaType(StrEnum):
    """Media types for heroes pages"""

    COMIC = "comic"
    SHORT_STORY = "short-story"
    VIDEO = "video"


class PlayerAchievementCategory(StrEnum):
    """Categories of achievements displayed in the players API"""

    GENERAL = "general"
    DAMAGE = "damage"
    TANK = "tank"
    SUPPORT = "support"
    MAPS = "maps"
    EVENTS = "events"


class PlayerGamemode(StrEnum):
    """Gamemodes associated with players statistics"""

    QUICKPLAY = "quickplay"
    COMPETITIVE = "competitive"


class PlayerPlatform(StrEnum):
    """Players platforms"""

    PC = "pc"
    PSN = "psn"
    XBL = "xbl"
    NINTENDO_SWITCH = "nintendo-switch"


class PlayerPrivacy(StrEnum):
    """Players career privacy"""

    PUBLIC = "public"
    PRIVATE = "private"


class Role(StrEnum):
    """Overwatch heroes roles"""

    DAMAGE = "damage"
    SUPPORT = "support"
    TANK = "tank"
