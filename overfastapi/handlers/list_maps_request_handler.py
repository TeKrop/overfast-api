"""List Maps Request Handler module"""
from overfastapi.config import HOME_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.maps_parser import MapsParser


class ListMapsRequestHandler(APIRequestHandler):
    """List Maps Request Handler used in order to retrieve a list of
    available Overwatch maps, using the MapsParser class.
    """

    parser_classes = [MapsParser]
    timeout = HOME_PATH_CACHE_TIMEOUT
