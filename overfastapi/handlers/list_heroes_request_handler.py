"""List Heroes Request Handler module"""
from overfastapi.config import HEROES_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.heroes_parser import HeroesParser


class ListHeroesRequestHandler(APIRequestHandler):
    """List Heroes Request Handler used in order to
    retrieve a list of available Overwatch heroes.
    """

    api_root_url = "/heroes"
    parser_classes = [HeroesParser]
    timeout = HEROES_PATH_CACHE_TIMEOUT
