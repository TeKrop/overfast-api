"""Set of enumerations of generic data displayed in the API :
heroes, gamemodes, etc.

"""
from enum import Enum


class StrEnum(str, Enum):
    """Generic Enum which will be casted easily as a string"""


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


class Role(StrEnum):
    """Overwatch heroes roles"""

    DAMAGE = "damage"
    SUPPORT = "support"
    TANK = "tank"
