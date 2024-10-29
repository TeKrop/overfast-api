"""List Roles Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.roles_parser import RolesParser


class ListRolesController(AbstractController):
    """List Roles Controller used in order to
    retrieve a list of available Overwatch roles.
    """

    parser_classes: ClassVar[list[type]] = [RolesParser]
    timeout = settings.heroes_path_cache_timeout
