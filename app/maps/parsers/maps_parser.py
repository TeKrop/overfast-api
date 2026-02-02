"""Maps Parser module"""

from typing import cast

from app.parsers import CSVParser


class MapsParser(CSVParser):
    """Overwatch maps list page Parser class"""

    filename = "maps"

    def parse_data(self) -> list[dict]:
        return [
            {
                "key": map_dict["key"],
                "name": map_dict["name"],
                "screenshot": self.get_static_url(map_dict["key"]),
                "gamemodes": map_dict["gamemodes"].split(","),
                "location": map_dict["location"],
                "country_code": map_dict.get("country_code") or None,
            }
            for map_dict in self.csv_data
        ]

    def filter_request_using_query(self, **kwargs) -> list:
        # Type assertion: we know parse_data returns list[dict]
        data = cast("list[dict]", self.data)
        gamemode = kwargs.get("gamemode")
        return (
            data
            if not gamemode
            else [map_dict for map_dict in data if gamemode in map_dict["gamemodes"]]
        )
