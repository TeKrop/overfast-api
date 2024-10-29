"""List Maps Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.maps_parser import MapsParser


class ListMapsController(AbstractController):
    """List Maps Controller used in order to retrieve a list of
    available Overwatch maps, using the MapsParser class.
    """

    parser_classes: ClassVar[list[type]] = [MapsParser]
    timeout = settings.csv_cache_timeout
