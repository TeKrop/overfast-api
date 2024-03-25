"""Player Stats Summary Request Handler module"""

from typing import ClassVar

from app.config import settings
from app.parsers.player_stats_summary_parser import PlayerStatsSummaryParser

from .api_request_handler import APIRequestHandler


class GetPlayerStatsSummaryRequestHandler(APIRequestHandler):
    """Player Stats Summary Request Handler used in order to retrieve essential
    stats of a player, often used for tracking progress : winrate, kda, damage, etc.
    Using the PlayerStatsSummaryParser.
    """

    parser_classes: ClassVar[list] = [PlayerStatsSummaryParser]
    timeout = settings.career_path_cache_timeout
