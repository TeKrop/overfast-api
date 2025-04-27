"""Player Career Controller module"""

from typing import ClassVar

from app.config import settings

from ..parsers.player_career_parser import PlayerCareerParser
from .base_player_controller import BasePlayerController


class GetPlayerCareerController(BasePlayerController):
    """Player Career Controller used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc. using the
    PlayerCareerParser class.
    """

    parser_classes: ClassVar[list] = [PlayerCareerParser]
    timeout = settings.career_path_cache_timeout
