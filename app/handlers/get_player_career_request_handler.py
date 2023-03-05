"""Player Career Request Handler module"""
from app.config import settings
from app.parsers.player_parser import PlayerParser

from .api_request_handler import APIRequestHandler


class GetPlayerCareerRequestHandler(APIRequestHandler):
    """Player Career Request Handler used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc. using the
    PlayerParser class.
    """

    parser_classes = [PlayerParser]
    timeout = settings.career_path_cache_timeout
