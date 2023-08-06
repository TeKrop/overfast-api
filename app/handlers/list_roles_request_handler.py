"""List Roles Request Handler module"""
from typing import ClassVar

from app.config import settings
from app.parsers.roles_parser import RolesParser

from .api_request_handler import APIRequestHandler


class ListRolesRequestHandler(APIRequestHandler):
    """List Roles Request Handler used in order to
    retrieve a list of available Overwatch roles.
    """

    parser_classes: ClassVar[list] = [RolesParser]
    timeout = settings.heroes_path_cache_timeout
