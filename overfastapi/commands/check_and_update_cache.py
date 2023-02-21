"""Command used in order to check and update Redis API Cache depending on
the expired cache refresh limit configuration. It can be run in the background.
"""
from fastapi import HTTPException

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.exceptions import ParserBlizzardError, ParserParsingError
from overfastapi.common.helpers import overfast_internal_error
from overfastapi.common.logging import logger
from overfastapi.config import BLIZZARD_HOST, PARSER_CACHE_KEY_PREFIX
from overfastapi.parsers.gamemodes_parser import GamemodesParser
from overfastapi.parsers.hero_parser import HeroParser
from overfastapi.parsers.heroes_parser import HeroesParser
from overfastapi.parsers.maps_parser import MapsParser
from overfastapi.parsers.player_parser import PlayerParser
from overfastapi.parsers.player_stats_summary_parser import PlayerStatsSummaryParser
from overfastapi.parsers.roles_parser import RolesParser

# Mapping of parser class names to linked classes
PARSER_CLASSES_MAPPING = {
    "GamemodesParser": GamemodesParser,
    "HeroParser": HeroParser,
    "HeroesParser": HeroesParser,
    "MapsParser": MapsParser,
    "PlayerParser": PlayerParser,
    "PlayerStatsSummaryParser": PlayerStatsSummaryParser,
    "RolesParser": RolesParser,
}

# Generic cache manager used in the process
cache_manager = CacheManager()


def get_soon_expired_cache_keys() -> set[str]:
    """Get a set of URIs for values in Parser Cache which are obsolete
    or will need to be updated.
    """
    return set(cache_manager.get_soon_expired_parser_cache_keys())


def get_request_parser_class(cache_key: str) -> tuple[type, dict]:
    """Get the request parser class and cache kwargs to use for instanciation"""
    cache_kwargs = {}

    specific_cache_key = cache_key.removeprefix(f"{PARSER_CACHE_KEY_PREFIX}:")
    parser_class_name = specific_cache_key.split("-")[0]
    cache_parser_class = PARSER_CLASSES_MAPPING[parser_class_name]

    # If the cache is related to local data
    if BLIZZARD_HOST not in specific_cache_key:
        return cache_parser_class, cache_kwargs

    uri = specific_cache_key.removeprefix(f"{parser_class_name}-{BLIZZARD_HOST}").split(
        "/"
    )
    cache_kwargs["locale"] = uri[1]
    if parser_class_name in ["PlayerParser", "PlayerStatsSummaryParser"]:
        cache_kwargs["player_id"] = uri[3]
    elif parser_class_name == "HeroParser":
        cache_kwargs["hero_key"] = uri[3]

    return cache_parser_class, cache_kwargs


def main():
    """Main method of the script"""
    logger.info("Starting Redis cache update...")

    keys_to_update = get_soon_expired_cache_keys()
    logger.info("Done ! Retrieved keys : {}", len(keys_to_update))

    for key in keys_to_update:
        logger.info("Updating data for {} key...", key)
        parser_class, kwargs = get_request_parser_class(key)

        parser = parser_class(**kwargs)

        try:
            parser.retrieve_and_parse_data()
        except ParserBlizzardError as error:
            logger.error(
                "Failed to instanciate Parser when refreshing : {}",
                error.message,
            )
        except ParserParsingError as error:
            overfast_internal_error(parser.blizzard_url, error)
        except HTTPException:
            continue

    logger.info("Redis cache update finished !")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="check_and_update_cache"))
    main()
