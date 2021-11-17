"""List Map Gamemodes Request Handler module"""
from overfastapi.config import MAPS_PATH, MAPS_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.map_gamemodes_parser import MapGamemodesParser


class ListMapGamemodesRequestHandler(APIRequestHandler):
    """List Map Gamemodes Request Handler used in order to retrieve a list of
    available Overwatch maps gamemodes, using the MapGamemodesParser class.
    """

    api_root_url = "/maps/gamemodes"
    root_path = MAPS_PATH
    parser_class = MapGamemodesParser
    timeout = MAPS_PATH_CACHE_TIMEOUT
