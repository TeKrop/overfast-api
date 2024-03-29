"""Heroes Stats Parser module"""

from typing import ClassVar

from .generics.csv_parser import CSVParser


class HeroesStatsParser(CSVParser):
    """Heroes stats (health, armor, shields) Parser class"""

    filename = "heroes"
    hitpoints_keys: ClassVar[set] = {"health", "armor", "shields"}

    def parse_data(self) -> dict:
        return {
            hero_stats["key"]: {"hitpoints": self.__get_hitpoints(hero_stats)}
            for hero_stats in self.csv_data
        }

    def __get_hitpoints(self, hero_stats: dict) -> dict:
        hitpoints = {hp_key: int(hero_stats[hp_key]) for hp_key in self.hitpoints_keys}
        hitpoints["total"] = sum(hitpoints.values())
        return hitpoints
