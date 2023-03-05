"""List Gamemodes Request Handler module"""
from app.config import settings
from app.parsers.gamemodes_parser import GamemodesParser

from .api_request_handler import APIRequestHandler


class ListGamemodesRequestHandler(APIRequestHandler):
    """List Gamemodes Request Handler used in order to retrieve a list of
    available Overwatch gamemodes, using the GamemodesParser class.
    """

    parser_classes = [GamemodesParser]
    timeout = settings.home_path_cache_timeout
