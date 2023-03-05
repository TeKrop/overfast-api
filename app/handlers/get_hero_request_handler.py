"""Hero Request Handler module"""
from app.config import settings
from app.parsers.hero_parser import HeroParser
from app.parsers.heroes_parser import HeroesParser

from .api_request_handler import APIRequestHandler


class GetHeroRequestHandler(APIRequestHandler):
    """Hero Request Handler used in order to retrieve data about a single
    Overwatch hero. The hero key given by the ListHeroesRequestHandler
    should be used to display data about a specific hero.
    """

    parser_classes = [HeroParser, HeroesParser]
    timeout = settings.hero_path_cache_timeout

    def merge_parsers_data(self, parsers_data: list[dict], **kwargs) -> dict:
        """Merge parsers data together : HeroParser for detailed data,
        and HeroParser for portrait (not here in the specific page)
        """
        hero_data = parsers_data[0]
        portrait_value = [
            hero["portrait"]
            for hero in parsers_data[1]
            if hero["key"] == kwargs.get("hero_key")
        ][0]

        # We want to insert the portrait before the "role" key
        role_pos = list(hero_data.keys()).index("role")
        hero_data_items = list(hero_data.items())
        hero_data_items.insert(role_pos, ("portrait", portrait_value))

        return dict(hero_data_items)
