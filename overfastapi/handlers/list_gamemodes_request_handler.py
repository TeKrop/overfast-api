"""List Gamemodes Request Handler module"""
from overfastapi.config import HOME_PATH, HOME_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.gamemodes_parser import GamemodesParser


class ListGamemodesRequestHandler(APIRequestHandler):
    """List Gamemodes Request Handler used in order to retrieve a list of
    available Overwatch gamemodes, using the GamemodesParser class.
    """

    api_root_url = "/gamemodes"
    root_path = HOME_PATH
    parser_class = GamemodesParser
    timeout = HOME_PATH_CACHE_TIMEOUT
