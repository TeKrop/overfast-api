"""Hero Request Handler module"""
from typing import ClassVar

from app.common.helpers import dict_insert_value_before_key
from app.config import settings
from app.parsers.hero_parser import HeroParser
from app.parsers.heroes_parser import HeroesParser
from app.parsers.heroes_stats_parser import HeroesStatsParser

from .api_request_handler import APIRequestHandler


class GetHeroRequestHandler(APIRequestHandler):
    """Hero Request Handler used in order to retrieve data about a single
    Overwatch hero. The hero key given by the ListHeroesRequestHandler
    should be used to display data about a specific hero.
    """

    parser_classes: ClassVar[list] = [HeroParser, HeroesParser, HeroesStatsParser]
    timeout = settings.hero_path_cache_timeout

    def merge_parsers_data(self, parsers_data: list[dict], **kwargs) -> dict:
        """Merge parsers data together :
        - HeroParser for detailed data
        - HeroesParser for portrait (not here in the specific page)
        - HeroesStatsParser for stats (health, armor, shields)
        """
        hero_data, heroes_data, heroes_stats_data = parsers_data

        try:
            portrait_value = next(
                hero["portrait"]
                for hero in heroes_data
                if hero["key"] == kwargs.get("hero_key")
            )
        except StopIteration:
            # The hero key may not be here in some specific edge cases,
            # for example if the hero has been released but is not in the
            # heroes list yet, or the list cache is outdated
            portrait_value = None
        else:
            # We want to insert the portrait before the "role" key
            hero_data = dict_insert_value_before_key(
                hero_data,
                "role",
                "portrait",
                portrait_value,
            )

        try:
            hitpoints = heroes_stats_data[kwargs.get("hero_key")]["hitpoints"]
        except KeyError:
            # Hero hitpoints may not be here if the CSV file
            # containing the data hasn't been updated
            hitpoints = None
        else:
            # We want to insert hitpoints before "abilities" key
            hero_data = dict_insert_value_before_key(
                hero_data,
                "abilities",
                "hitpoints",
                hitpoints,
            )

        return hero_data
