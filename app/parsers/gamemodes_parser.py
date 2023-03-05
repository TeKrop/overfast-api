"""Gamemodes Parser module"""
from app.config import settings

from .api_parser import APIParser


class GamemodesParser(APIParser):
    """Overwatch map gamemodes list page Parser class"""

    root_path = settings.home_path
    timeout = settings.home_path_cache_timeout

    def parse_data(self) -> list[dict]:
        gamemodes_container = (
            self.root_tag.find("div", class_="maps", recursive=False)
            .find("blz-carousel-section", recursive=False)
            .find("blz-carousel", recursive=False)
        )

        gamemodes_extras = [
            {
                "key": feature_div["label"],
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
                "key": gamemodes_extras[gamemode_index]["key"],
                "name": gamemode_div.get_text(),
                "icon": gamemode_div.find("blz-image")["src:min-plus"],
                "description": gamemodes_extras[gamemode_index]["description"],
                "screenshot": gamemodes_extras[gamemode_index]["screenshot"],
            }
            for gamemode_index, gamemode_div in enumerate(
                gamemodes_container.find("blz-tab-controls").find_all("blz-tab-control")
            )
        ]
