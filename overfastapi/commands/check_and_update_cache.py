"""Command used in order to check and update Redis API Cache depending on
the expired cache refresh limit configuration. It can be run in the background.
"""

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import HeroKey
from overfastapi.common.logging import logger
from overfastapi.handlers.get_hero_request_handler import GetHeroRequestHandler
from overfastapi.handlers.get_player_career_request_handler import (
    GetPlayerCareerRequestHandler,
)
from overfastapi.handlers.list_heroes_request_handler import ListHeroesRequestHandler
from overfastapi.handlers.list_map_gamemodes_request_handler import (
    ListMapGamemodesRequestHandler,
)
from overfastapi.handlers.list_maps_request_handler import ListMapsRequestHandler

PREFIXES_HANDLERS_MAPPING = {
    "/heroes": ListHeroesRequestHandler,
    **{f"/heroes/{hero_key}": GetHeroRequestHandler for hero_key in HeroKey},
    "/maps": ListMapsRequestHandler,
    "/maps/gamemodes": ListMapGamemodesRequestHandler,
    "/players": GetPlayerCareerRequestHandler,
}


def get_soon_expired_cache_keys() -> set[str]:
    """Get a set of URIs for values in API Cache which will expire soon
    without taking subroutes and query parameters"""
    cache_manager = CacheManager()
    return set(
        # api-cache:/heroes?role=damage => /heroes?role=damage => /heroes
        key.split(":")[1].split("?")[0]
        for key in cache_manager.get_soon_expired_api_cache_keys()
        # Avoid players subroutes
        if key.split("/")[-1].split("?")[0] not in ("summary", "stats", "achievements")
    )


def get_request_handler_class_and_kwargs(cache_key: str) -> tuple[type, dict]:
    """Get the request handler class and cache kwargs (to give to the
    update_all_cache() method) associated with a given cache key
    """
    cache_request_handler_class = None
    cache_kwargs = {}

    uri = cache_key.split("/")
    if cache_key.startswith("/players"):
        # /players/pc/Player-1234 => ["", "players", "pc" "Player-1234"]
        cache_request_handler_class = PREFIXES_HANDLERS_MAPPING["/players"]
        cache_kwargs = {"platform": uri[2], "player_id": uri[3]}
    elif cache_key.startswith("/heroes") and len(uri) > 2:
        cache_request_handler_class = PREFIXES_HANDLERS_MAPPING[cache_key]
        cache_kwargs = {"hero_key": uri[2]}
    else:
        cache_request_handler_class = PREFIXES_HANDLERS_MAPPING[cache_key]

    return cache_request_handler_class, cache_kwargs


def main():
    """Main method of the script"""
    logger.info(
        "Starting Redis cache update...\n"
        "Retrieving cache keys which will expire soon..."
    )
    soon_expired_cache_keys = get_soon_expired_cache_keys()
    logger.info("Done ! Retrieved keys : {}", len(soon_expired_cache_keys))

    for key in soon_expired_cache_keys:
        logger.info("Updating all cache for {} key...", key)
        request_handler_class, kwargs = get_request_handler_class_and_kwargs(key)
        request_handler_class().update_all_cache(parser=None, **kwargs)

    logger.info("Redis cache update finished !")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="check_and_update_cache"))
    main()
