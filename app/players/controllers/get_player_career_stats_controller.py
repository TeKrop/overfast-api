"""Player Stats Summary Controller module"""

from typing import ClassVar

from app.config import settings

from ..parsers.player_career_stats_parser import PlayerCareerStatsParser
from .base_player_controller import BasePlayerController


class GetPlayerCareerStatsController(BasePlayerController):
    """Player Career Stats Controller used in order to retrieve career
    statistics of a player without labels, easily explorable
    """

    parser_classes: ClassVar[list] = [PlayerCareerStatsParser]
    timeout = settings.career_path_cache_timeout
