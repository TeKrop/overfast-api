"""Player Stats Summary Controller module"""

from typing import ClassVar

from app.config import settings

from ..parsers.player_stats_summary_parser import PlayerStatsSummaryParser
from .base_player_controller import BasePlayerController


class GetPlayerStatsSummaryController(BasePlayerController):
    """Player Stats Summary Controller used in order to retrieve essential
    stats of a player, often used for tracking progress : winrate, kda, damage, etc.
    Using the PlayerStatsSummaryParser.
    """

    parser_classes: ClassVar[list] = [PlayerStatsSummaryParser]
    timeout = settings.career_path_cache_timeout
