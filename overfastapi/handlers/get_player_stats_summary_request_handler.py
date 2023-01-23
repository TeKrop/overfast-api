"""Player Stats Summary Request Handler module"""
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
