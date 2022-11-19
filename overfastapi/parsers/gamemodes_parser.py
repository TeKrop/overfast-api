"""Gamemodes Parser module"""
from functools import cached_property

from overfastapi.config import HOME_PATH
from overfastapi.parsers.api_parser import APIParser


class GamemodesParser(APIParser):
    """Overwatch map gamemodes list page Parser class"""

    root_path = HOME_PATH

    @cached_property
    def cache_key(self) -> str:
        return f"gamemodes-{self.blizzard_url}"

    def parse_data(self) -> list:
        gamemodes_container = (
            self.root_tag.find("div", class_="maps", recursive=False)
            .find("blz-carousel-section", recursive=False)
            .find("blz-carousel", recursive=False)
        )

        gamemodes_extras = [
            {
                "description": (
                    feature_div.find("blz-header")
                    .find("div", slot="description")
                    .get_text()
                    .strip()
                ),
                "screenshot": feature_div.find("blz-image")["src:min-plus"],
            }
            for feature_div in gamemodes_container.find_all("blz-feature")
        ]

        return [
            {
                "name": gamemode_div.get_text(),
                "icon": gamemode_div.find("blz-image")["src:min-plus"],
                "description": gamemodes_extras[gamemode_index]["description"],
                "screenshot": gamemodes_extras[gamemode_index]["screenshot"],
            }
            for gamemode_index, gamemode_div in enumerate(
                gamemodes_container.find("blz-tab-controls").find_all("blz-tab-control")
            )
        ]
