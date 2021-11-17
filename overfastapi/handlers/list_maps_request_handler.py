"""List Maps Request Handler module"""
from overfastapi.common.enums import MapGamemode
from overfastapi.config import MAPS_PATH, MAPS_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.maps_parser import MapsParser


class ListMapsRequestHandler(APIRequestHandler):
    """List Maps Request Handler used in order to retrieve a list of
    available Overwatch maps, using the MapsParser class.
    """

    api_root_url = "/maps"
    root_path = MAPS_PATH
    parser_class = MapsParser
    timeout = MAPS_PATH_CACHE_TIMEOUT
    route_filters = [
        {"uri": f"?gamemode={gamemode.value}", "kwargs": {"gamemode": gamemode.value}}
        for gamemode in MapGamemode
    ]

    @staticmethod
    def filter_request_using_query(parsed_data: list, **kwargs) -> list[dict]:
        gamemode = kwargs.get("gamemode")
        return (
            parsed_data
            if not gamemode
            else [ow_map for ow_map in parsed_data if gamemode in ow_map["gamemodes"]]
        )
