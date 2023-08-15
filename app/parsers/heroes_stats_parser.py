"""Heroes Stats Parser module"""
from typing import ClassVar

from app.common.helpers import read_csv_data_file
from app.config import settings

from .abstract_parser import AbstractParser


class HeroesStatsParser(AbstractParser):
    """Heroes stats (health, armor, shields) Parser class"""

    timeout = settings.hero_path_cache_timeout
    hitpoints_keys: ClassVar[set] = {"health", "armor", "shields"}

    async def retrieve_and_parse_data(self) -> None:
        heroes_stats_data = read_csv_data_file("heroes.csv")

        self.data = {
            hero_stats["key"]: {"hitpoints": self.__get_hitpoints(hero_stats)}
            for hero_stats in heroes_stats_data
        }

        # Update the Parser Cache
        self.cache_manager.update_parser_cache(self.cache_key, self.data, self.timeout)

    def __get_hitpoints(self, hero_stats: dict) -> dict:
        hitpoints = {hp_key: int(hero_stats[hp_key]) for hp_key in self.hitpoints_keys}
        hitpoints["total"] = sum(hitpoints.values())
        return hitpoints
