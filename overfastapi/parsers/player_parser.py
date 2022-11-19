"""Player profile page Parser module"""
from fastapi import status

from overfastapi.common.exceptions import ParserInitError
from overfastapi.config import CAREER_PATH
from overfastapi.parsers.api_parser import APIParser


class PlayerParser(APIParser):
    """Overwatch player profile page Parser class"""

    root_path = CAREER_PATH

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_id = kwargs.get("player_id")

        # We must check if we have expected section
        if not self.root_tag.find("section", id="overview-section"):
            raise ParserInitError(
                status_code=status.HTTP_404_NOT_FOUND, message="Player not found"
            )

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{self.blizzard_root_url}/{kwargs.get('platform')}/{kwargs.get('player_id')}"

    def parse_data(self) -> dict:
        return {}

    def filter_request_using_query(self, **kwargs) -> dict:
        if kwargs.get("summary"):
            return self.data.get("summary")

        if kwargs.get("stats"):
            hero_filter = kwargs.get("hero")
            return {
                hero_key: statistics
                for hero_key, statistics in (
                    (
                        (self.data.get(kwargs.get("gamemode")) or {}).get(
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
                    (self.data.get("achievements") or {}).items()
                )
                if not category_filter or category_filter == category_key
            }

        return self.data
