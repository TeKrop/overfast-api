"""Set of enumerations of generic data displayed in the API :
heroes, gamemodes, etc.

"""

from enum import StrEnum


class RouteTag(StrEnum):
    """Tags used to classify API routes"""

    HEROES = "🦸 Heroes"
    GAMEMODES = "🎲 Gamemodes"
    MAPS = "🗺️ Maps"
    PLAYERS = "🎮 Players"


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
