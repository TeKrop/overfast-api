"""Player Stats Summary Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.player_career_parser import PlayerCareerParser


class GetPlayerCareerStatsController(AbstractController):
    """Player Career Stats Controller used in order to retrieve career
    statistics of a player without labels, easily explorable
    """

    parser_classes: ClassVar[list] = [PlayerCareerParser]
    timeout = settings.career_path_cache_timeout
