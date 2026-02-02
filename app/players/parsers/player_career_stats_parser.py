"""Player stats summary Parser module"""

from .player_career_parser import PlayerCareerParser


class PlayerCareerStatsParser(PlayerCareerParser):
    """Overwatch player career Parser class"""

    def filter_request_using_query(self, **_) -> dict:
        return self._filter_stats() if self.data else {}

    def _compute_parsed_data(self) -> dict:
        # Only return career stats, which will be used for calculation
        # depending on the parameters
        return self.__get_career_summary_stats(self.get_stats()) or {}

    def __get_career_summary_stats(self, raw_stats: dict | None) -> dict:
        if not raw_stats:
            return {}

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
