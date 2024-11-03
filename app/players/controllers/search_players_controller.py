"""Search Players Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.player_search_parser import PlayerSearchParser


class SearchPlayersController(AbstractController):
    """Search Players Controller used in order to find an Overwatch player

    Some others parsers are used, but only to compute already downloaded data, we
    don't want them to retrieve Blizzard data as when we call their
    general parse() method.
    """

    parser_classes: ClassVar[list] = [PlayerSearchParser]
    timeout = settings.search_account_path_cache_timeout
