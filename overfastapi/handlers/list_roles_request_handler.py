"""List Roles Request Handler module"""
from overfastapi.config import HEROES_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.roles_parser import RolesParser


class ListRolesRequestHandler(APIRequestHandler):
    """List Roles Request Handler used in order to
    retrieve a list of available Overwatch roles.
    """

    parser_classes = [RolesParser]
    timeout = HEROES_PATH_CACHE_TIMEOUT
