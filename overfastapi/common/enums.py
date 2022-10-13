"""Set of enumerations of generic data displayed in the API :
heroes, gamemodes, etc.

"""
from enum import StrEnum


class RouteTag(StrEnum):
    """Tags used to classify API routes"""

    HEROES = "Heroes"
    MAPS = "Maps"
    PLAYERS = "Players"


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
    RAMATTRA = "ramattra"
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


class Role(StrEnum):
    """Overwatch heroes roles"""

    DAMAGE = "damage"
    SUPPORT = "support"
    TANK = "tank"


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


class CompetitiveDivision(StrEnum):
    """Competitive division of a rank"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
