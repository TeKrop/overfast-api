"""Maps Parser module"""
from overfastapi.common.helpers import read_csv_data_file
from overfastapi.config import HOME_PATH_CACHE_TIMEOUT, OVERFAST_API_BASE_URL
from overfastapi.parsers.abstract_parser import AbstractParser


class MapsParser(AbstractParser):
    """Overwatch maps list page Parser class"""

    timeout = HOME_PATH_CACHE_TIMEOUT

    def retrieve_and_parse_data(self) -> None:
        maps_data = read_csv_data_file("maps.csv")

        self.data = [
            {
                "name": map_dict["name"],
                "screenshot": self.get_screenshot_url(map_dict["key"]),
                "gamemodes": map_dict["gamemodes"].split(","),
                "location": map_dict["location"],
                "country_code": map_dict["country_code"] or None,
            }
            for map_dict in maps_data
        ]

        # Update the Parser Cache
        self.cache_manager.update_parser_cache(self.cache_key, self.data, self.timeout)

    def filter_request_using_query(self, **kwargs) -> list:
        gamemode = kwargs.get("gamemode")
        return (
            self.data
            if not gamemode
            else [
                map_dict for map_dict in self.data if gamemode in map_dict["gamemodes"]
            ]
        )

    def get_screenshot_url(self, map_key: str) -> str:
        return f"{OVERFAST_API_BASE_URL}/static/maps/{map_key}.jpg"
