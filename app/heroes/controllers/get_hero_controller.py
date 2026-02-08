"""Hero Controller module"""

from typing import Any, ClassVar

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.hero import parse_hero
from app.adapters.blizzard.parsers.heroes import parse_heroes
from app.adapters.blizzard.parsers.heroes_stats import parse_heroes_stats
from app.config import settings
from app.controllers import AbstractController
from app.enums import Locale


class GetHeroController(AbstractController):
    """Hero Controller used in order to retrieve data about a single
    Overwatch hero.
    """

    parser_classes: ClassVar[list[type]] = []
    timeout = settings.hero_path_cache_timeout

    async def process_request(self, **kwargs) -> dict:
        """Process request using stateless parser functions"""
        hero_key = kwargs.get("hero_key")
        locale = kwargs.get("locale") or Locale.ENGLISH_US

        client = BlizzardClient()

        # Fetch data from all three sources
        hero_data = await parse_hero(client, hero_key, locale)
        heroes_list = await parse_heroes(client, locale)
        heroes_stats = parse_heroes_stats()

        # Merge data
        data = self._merge_hero_data(hero_data, heroes_list, heroes_stats, hero_key)

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data

    @staticmethod
    def _merge_hero_data(
        hero_data: dict,
        heroes_list: list[dict],
        heroes_stats: dict,
        hero_key: str,
    ) -> dict:
        """
        Merge data from hero details, heroes list, and heroes stats

        Args:
            hero_data: Detailed hero data from hero parser
            heroes_list: List of all heroes (for portrait)
            heroes_stats: Stats dict (for hitpoints)
            hero_key: Hero key for lookups
        """
        # Add portrait from heroes list
        try:
            portrait_value = next(
                hero["portrait"] for hero in heroes_list if hero["key"] == hero_key
            )
        except StopIteration:
            # The hero key may not be here in some specific edge cases,
            # for example if the hero has been released but is not in the
            # heroes list yet, or the list cache is outdated
            portrait_value = None
        else:
            hero_data = dict_insert_value_before_key(
                hero_data,
                "role",
                "portrait",
                portrait_value,
            )

        # Add hitpoints from stats
        try:
            hitpoints = heroes_stats[hero_key]["hitpoints"]
        except KeyError:
            # Hero hitpoints may not be here if the CSV file
            # containing the data hasn't been updated
            hitpoints = None
        else:
            hero_data = dict_insert_value_before_key(
                hero_data,
                "abilities",
                "hitpoints",
                hitpoints,
            )

        return hero_data

    # Keep legacy method name for backward compatibility with tests
    @staticmethod
    def _dict_insert_value_before_key(
        data: dict,
        key: str,
        new_key: str,
        new_value: Any,
    ) -> dict:
        """Backward compatibility wrapper for tests"""
        return dict_insert_value_before_key(data, key, new_key, new_value)


def dict_insert_value_before_key(
    data: dict,
    key: str,
    new_key: str,
    new_value: Any,
) -> dict:
    """Insert a given key/value pair before another key in a given dict"""
    if key not in data:
        raise KeyError

    key_pos = list(data.keys()).index(key)
    data_items = list(data.items())
    data_items.insert(key_pos, (new_key, new_value))

    return dict(data_items)
