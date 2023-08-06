"""Player Stats Summary Request Handler module"""
from typing import ClassVar

from app.config import settings
from app.parsers.player_career_parser import PlayerCareerParser

from .api_request_handler import APIRequestHandler


class GetPlayerCareerStatsRequestHandler(APIRequestHandler):
    """Player Career Stats Request Handler used in order to retrieve career
    statistics of a player without labels, easily explorable
    """

    parser_classes: ClassVar[list] = [PlayerCareerParser]
    timeout = settings.career_path_cache_timeout
