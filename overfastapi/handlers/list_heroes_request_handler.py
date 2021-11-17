"""List Heroes Request Handler module"""
from overfastapi.common.enums import Role
from overfastapi.config import HEROES_PATH, HEROES_PATH_CACHE_TIMEOUT
from overfastapi.handlers.api_request_handler import APIRequestHandler
from overfastapi.parsers.heroes_parser import HeroesParser


class ListHeroesRequestHandler(APIRequestHandler):
    """List Heroes Request Handler used in order to retrieve a list of
    available Overwatch heroes, using the HeroesParser class.
    """

    api_root_url = "/heroes"
    root_path = HEROES_PATH
    parser_class = HeroesParser
    timeout = HEROES_PATH_CACHE_TIMEOUT
    route_filters = [
        {"uri": f"?role={role.value}", "kwargs": {"role": role.value}} for role in Role
    ]

    @staticmethod
    def filter_request_using_query(parsed_data: list, **kwargs) -> list[dict]:
        role = kwargs.get("role")
        return (
            parsed_data
            if not role
            else [hero_dict for hero_dict in parsed_data if hero_dict["role"] == role]
        )
