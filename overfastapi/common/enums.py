"""Set of enumerations of generic data displayed in the API :
heroes, gamemodes, etc.

"""
from enum import StrEnum


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


class HeroKeyCareerFilter(StrEnum):
    """Hero keys filter for career statistics endpoint"""

    ALL_HEROES = "all-heroes"
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
