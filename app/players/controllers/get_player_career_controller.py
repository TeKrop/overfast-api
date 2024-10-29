"""Player Career Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.player_parser import PlayerParser


class GetPlayerCareerController(AbstractController):
    """Player Career Controller used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc. using the
    PlayerParser class.
    """

    parser_classes: ClassVar[list] = [PlayerParser]
    timeout = settings.career_path_cache_timeout
