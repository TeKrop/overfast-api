"""List Maps Request Handler module"""
from typing import ClassVar

from app.config import settings
from app.parsers.maps_parser import MapsParser

from .api_request_handler import APIRequestHandler


class ListMapsRequestHandler(APIRequestHandler):
    """List Maps Request Handler used in order to retrieve a list of
    available Overwatch maps, using the MapsParser class.
    """

    parser_classes: ClassVar[list] = [MapsParser]
    timeout = settings.home_path_cache_timeout
