"""Player Career Request Handler module"""
from overfastapi.common.enums import HeroKey, PlayerAchievementCategory, PlayerGamemode
from overfastapi.config import CAREER_PATH, CAREER_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.player_parser import PlayerParser


class GetPlayerCareerRequestHandler(APIRequestHandler):
    """Player Career Request Handler used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, achievements, etc. using the
    PlayerParser class.
    """

    api_root_url = "/players"
    root_path = CAREER_PATH
    parser_class = PlayerParser
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

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{self.blizzard_root_url}/{kwargs.get('platform')}/{kwargs.get('player_id')}"

    def get_api_request_url(self, **kwargs) -> str:
        return f"{self.api_root_url}/{kwargs.get('platform')}/{kwargs.get('player_id')}"

    @staticmethod
    def filter_request_using_query(parsed_data: dict, **kwargs) -> dict:
        if kwargs.get("summary"):
            return parsed_data.get("summary")

        if kwargs.get("stats"):
            hero_filter = kwargs.get("hero")
            return {
                hero_key: statistics
                for hero_key, statistics in (
                    (
                        (parsed_data.get(kwargs.get("gamemode")) or {}).get(
                            "career_stats"
                        )
                        or {}
                    ).items()
                )
                if not hero_filter or hero_filter == hero_key
            }

        if kwargs.get("achievements"):
            category_filter = kwargs.get("category")
            return {
                category_key: achievements
                for category_key, achievements in (
                    (parsed_data.get("achievements") or {}).items()
                )
                if not category_filter or category_filter == category_key
            }

        return parsed_data
