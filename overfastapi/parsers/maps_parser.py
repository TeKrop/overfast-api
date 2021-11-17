"""Maps page Parser module"""
import json

from overfastapi.parsers.api_parser import APIParser


class MapsParser(APIParser):
    """Overwatch maps list page Parser class"""

    def parse_data(self) -> list:
        maps_wrapper = self.root_tag.find("section", id="maps-section").find(
            "div", class_="Maps-wrapper"
        )

        return [
            {
                "name": map_details["data-title"],
                "gamemodes": json.loads(map_details["data-map-types"]),
                "thumbnail": map_details.find(
                    "div", class_="Card-thumbnail-wrapper"
                ).find("img")["src"],
                "flag": map_details.find("span", class_="Map-flag").find("img")["src"],
            }
            for map_details in maps_wrapper.find_all("a", class_="Map")
        ]
