"""Player Career Request Handler module"""
from overfastapi.common.enums import HeroKey, PlayerAchievementCategory, PlayerGamemode
from overfastapi.config import CAREER_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.player_parser import PlayerParser


class GetPlayerCareerRequestHandler(APIRequestHandler):
    """Player Career Request Handler used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, achievements, etc. using the
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
                "kwargs": {"gamemode": gamemode.value, "stats": True},
            }
            for gamemode in PlayerGamemode
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
            for hero in HeroKey
        ],
        {"uri": "/achievements", "kwargs": {"achievements": True}},
        *[
            {
                "uri": f"/achievements?category={category.value}",
                "kwargs": {"category": category.value, "achievements": True},
            }
            for category in PlayerAchievementCategory
        ],
    ]

    def get_api_request_url(self, **kwargs) -> str:
        return f"{self.api_root_url}/{kwargs.get('platform')}/{kwargs.get('player_id')}"
