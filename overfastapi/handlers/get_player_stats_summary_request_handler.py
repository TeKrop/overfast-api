"""Player Stats Summary Request Handler module"""
from overfastapi.common.enums import PlayerGamemode, PlayerPlatform
from overfastapi.handlers.get_player_career_request_handler import (
    GetPlayerCareerRequestHandler,
)
from overfastapi.parsers.player_stats_summary_parser import PlayerStatsSummaryParser


class GetPlayerStatsSummaryRequestHandler(GetPlayerCareerRequestHandler):
    """Player Stats Summary Request Handler used in order to retrieve essential
    stats of a player, often used for tracking progress : winrate, kda, damage, etc.
    Using the PlayerStatsSummaryParser.
    """

    parser_classes = [PlayerStatsSummaryParser]
    route_filters = [
        *[
            {
                "uri": f"?gamemode={gamemode.value}",
                "kwargs": {"gamemode": gamemode.value},
            }
            for gamemode in PlayerGamemode
        ],
        *[
            {
                "uri": f"?platform={platform.value}",
                "kwargs": {"platform": platform.value},
            }
            for platform in PlayerPlatform
        ],
        *[
            {
                "uri": f"?gamemode={gamemode.value}&platform={platform.value}",
                "kwargs": {"gamemode": gamemode.value, "platform": platform.value},
            }
            for gamemode in PlayerGamemode
            for platform in PlayerPlatform
        ],
    ]

    def get_api_request_url(self, **kwargs) -> str:
        return f"{self.api_root_url}/{kwargs.get('player_id')}/stats/summary"
