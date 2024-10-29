"""List Heroes Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.heroes_parser import HeroesParser


class ListHeroesController(AbstractController):
    """List Heroes Controller used in order to
    retrieve a list of available Overwatch heroes.
    """

    parser_classes: ClassVar[list[type]] = [HeroesParser]
    timeout = settings.heroes_path_cache_timeout
