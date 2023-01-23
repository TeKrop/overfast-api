"""Player Career Request Handler module"""
from overfastapi.config import CAREER_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.player_parser import PlayerParser


class GetPlayerCareerRequestHandler(APIRequestHandler):
    """Player Career Request Handler used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc. using the
    PlayerParser class.
    """

    api_root_url = "/players"
    parser_classes = [PlayerParser]
    timeout = CAREER_PATH_CACHE_TIMEOUT
