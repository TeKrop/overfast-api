"""List Heroes Request Handler module"""
from typing import ClassVar

from app.config import settings
from app.parsers.heroes_parser import HeroesParser

from .api_request_handler import APIRequestHandler


class ListHeroesRequestHandler(APIRequestHandler):
    """List Heroes Request Handler used in order to
    retrieve a list of available Overwatch heroes.
    """

    parser_classes: ClassVar[list] = [HeroesParser]
    timeout = settings.heroes_path_cache_timeout
