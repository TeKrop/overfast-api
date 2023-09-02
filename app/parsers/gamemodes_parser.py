"""Gamemodes Parser module"""

from .generics.csv_parser import CSVParser


class GamemodesParser(CSVParser):
    """Overwatch map gamemodes list page Parser class"""

    filename = "gamemodes"

    def parse_data(self) -> list[dict]:
        return [
            {
                "key": gamemode["key"],
                "name": gamemode["name"],
                "icon": self.get_static_url(
                    f"{gamemode['key']}-icon",
                    extension="svg",
                ),
                "description": gamemode["description"],
                "screenshot": self.get_static_url(
                    gamemode["key"],
                    extension="avif",
                ),
            }
            for gamemode in self.csv_data
        ]
