"""Hero Request Handler module"""
from overfastapi.config import HERO_PATH_CACHE_TIMEOUT, HEROES_PATH
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.hero_parser import HeroParser


class GetHeroRequestHandler(APIRequestHandler):
    """Hero Request Handler used in order to retrieve data about a single
    Overwatch hero, using the HeroParser class. The hero key given by the
    ListHeroesRequestHandler should be used to display data about a specific hero.
    """

    api_root_url = "/heroes"
    root_path = HEROES_PATH
    parser_class = HeroParser
    timeout = HERO_PATH_CACHE_TIMEOUT

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{self.blizzard_root_url}/{kwargs.get('hero_key')}"

    def get_api_request_url(self, **kwargs) -> str:
        return f"{self.api_root_url}/{kwargs.get('hero_key')}"
