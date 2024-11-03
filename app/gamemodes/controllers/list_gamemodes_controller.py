"""List Gamemodes Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController
from app.gamemodes.parsers.gamemodes_parser import GamemodesParser


class ListGamemodesController(AbstractController):
    """List Gamemodes Controller used in order to retrieve a list of
    available Overwatch gamemodes, using the GamemodesParser class.
    """

    parser_classes: ClassVar[list[type]] = [GamemodesParser]
    timeout = settings.csv_cache_timeout
