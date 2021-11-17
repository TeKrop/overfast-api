"""Map Gamemodes Parser module"""
from overfastapi.parsers.api_parser import APIParser


class MapGamemodesParser(APIParser):
    """Overwatch map gamemodes list page Parser class"""

    def parse_data(self) -> list:
        maps_filters = self.root_tag.find(
            "section", id="maps-information-section"
        ).find("div", class_="MapsFilters")

        return [
            {
                "key": map_filter["data-filter"],
                "name": map_filter["data-title"],
                "description": map_filter["data-description"],
            }
            for map_filter in maps_filters.find_all("a", class_="MapFilter")
            if map_filter["data-filter"] != "all"
        ]
