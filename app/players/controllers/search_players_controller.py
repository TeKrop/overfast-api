"""Search Players Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.player_search_parser import PlayerSearchParser


class SearchPlayersController(AbstractController):
    """Search Players Controller used in order to find an Overwatch player"""

    parser_classes: ClassVar[list] = [PlayerSearchParser]
    timeout = settings.search_account_path_cache_timeout
