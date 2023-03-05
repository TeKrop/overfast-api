"""Player Stats Summary Request Handler module"""
from app.parsers.player_stats_summary_parser import PlayerStatsSummaryParser

from .get_player_career_request_handler import GetPlayerCareerRequestHandler


class GetPlayerStatsSummaryRequestHandler(GetPlayerCareerRequestHandler):
    """Player Stats Summary Request Handler used in order to retrieve essential
    stats of a player, often used for tracking progress : winrate, kda, damage, etc.
    Using the PlayerStatsSummaryParser.
    """

    parser_classes = [PlayerStatsSummaryParser]
