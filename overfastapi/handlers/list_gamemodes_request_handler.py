"""List Gamemodes Request Handler module"""
from overfastapi.config import HOME_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.gamemodes_parser import GamemodesParser


class ListGamemodesRequestHandler(APIRequestHandler):
    """List Gamemodes Request Handler used in order to retrieve a list of
    available Overwatch gamemodes, using the GamemodesParser class.
    """

    parser_classes = [GamemodesParser]
    timeout = HOME_PATH_CACHE_TIMEOUT
