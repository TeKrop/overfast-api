"""Player Career Request Handler module"""
from overfastapi.common.enums import HeroKeyCareerFilter, PlayerGamemode, PlayerPlatform
from overfastapi.config import CAREER_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.player_parser import PlayerParser


class GetPlayerCareerRequestHandler(APIRequestHandler):
    """Player Career Request Handler used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc. using the
    PlayerParser class.
    """

    api_root_url = "/players"
    parser_classes = [PlayerParser]
    timeout = CAREER_PATH_CACHE_TIMEOUT
    route_filters = [
        {"uri": "/summary", "kwargs": {"summary": True}},
        *[
            {
                "uri": f"/stats?gamemode={gamemode.value}",
                "kwargs": {
                    "gamemode": gamemode.value,
                    "stats": True,
                },
            }
            for gamemode in PlayerGamemode
        ],
        *[
            {
                "uri": f"/stats?gamemode={gamemode.value}&platform={platform.value}",
                "kwargs": {
                    "gamemode": gamemode.value,
                    "platform": platform.value,
                    "stats": True,
                },
            }
            for gamemode in PlayerGamemode
            for platform in PlayerPlatform
        ],
        *[
            {
                "uri": f"/stats?gamemode={gamemode.value}&hero={hero.value}",
                "kwargs": {
                    "gamemode": gamemode.value,
                    "hero": hero.value,
                    "stats": True,
                },
            }
            for gamemode in PlayerGamemode
            for hero in HeroKeyCareerFilter
        ],
        *[
            {
                "uri": (
                    "/stats?"
                    f"gamemode={gamemode.value}"
                    f"&platform={platform.value}"
                    f"&hero={hero.value}"
                ),
                "kwargs": {
                    "gamemode": gamemode.value,
                    "platform": platform.value,
                    "hero": hero.value,
                    "stats": True,
                },
            }
            for gamemode in PlayerGamemode
            for platform in PlayerPlatform
            for hero in HeroKeyCareerFilter
        ],
    ]

    def get_api_request_url(self, **kwargs) -> str:
        return f"{self.api_root_url}/{kwargs.get('player_id')}"
