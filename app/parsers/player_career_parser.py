"""Player stats summary Parser module"""

from fastapi import status

from app.common.exceptions import ParserBlizzardError

from .player_parser import PlayerParser


class PlayerCareerParser(PlayerParser):
    """Overwatch player career Parser class"""

    def filter_request_using_query(self, **kwargs) -> dict:
        return self._filter_stats(**kwargs) if self.data else {}

    def parse_data(self) -> dict | None:
        # We must check if we have the expected section for profile. If not,
        # it means the player doesn't exist or hasn't been found.
        if not self.root_tag.find("blz-section", class_="Profile-masthead"):
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Player not found",
            )

        # Only return heroes stats, which will be used for calculation
        # depending on the parameters
        return self.__get_career_stats(self.get_stats())

    def __get_career_stats(self, raw_stats: dict | None) -> dict | None:
        if not raw_stats:
            return None

        return {
            "stats": {
                platform: {
                    gamemode: {
                        "career_stats": {
                            hero_key: (
                                {
                                    stat_group["category"]: {
                                        stat["key"]: stat["value"]
                                        for stat in stat_group["stats"]
                                    }
                                    for stat_group in statistics
                                }
                                if statistics
                                else None
                            )
                            for hero_key, statistics in gamemode_stats[
                                "career_stats"
                            ].items()
                        },
                    }
                    for gamemode, gamemode_stats in platform_stats.items()
                    if gamemode_stats
                }
                for platform, platform_stats in raw_stats.items()
                if platform_stats
            },
        }
