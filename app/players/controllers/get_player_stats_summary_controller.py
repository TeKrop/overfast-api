"""Player Stats Summary Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.player_stats_summary_parser import PlayerStatsSummaryParser


class GetPlayerStatsSummaryController(AbstractController):
    """Player Stats Summary Controller used in order to retrieve essential
    stats of a player, often used for tracking progress : winrate, kda, damage, etc.
    Using the PlayerStatsSummaryParser.
    """

    parser_classes: ClassVar[list] = [PlayerStatsSummaryParser]
    timeout = settings.career_path_cache_timeout
