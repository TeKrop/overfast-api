"""Command used in order to check and update Redis API Cache depending on
the expired cache refresh limit configuration. It can be run in the background.
"""
import asyncio

from fastapi import HTTPException

from app.common.cache_manager import CacheManager
from app.common.exceptions import ParserBlizzardError, ParserParsingError
from app.common.helpers import overfast_internal_error
from app.common.logging import logger
from app.config import settings
from app.parsers.abstract_parser import AbstractParser
from app.parsers.gamemodes_parser import GamemodesParser
from app.parsers.hero_parser import HeroParser
from app.parsers.heroes_parser import HeroesParser
from app.parsers.maps_parser import MapsParser
from app.parsers.namecard_parser import NamecardParser
from app.parsers.player_parser import PlayerParser
from app.parsers.player_stats_summary_parser import PlayerStatsSummaryParser
from app.parsers.roles_parser import RolesParser

# Mapping of parser class names to linked classes
PARSER_CLASSES_MAPPING = {
    "GamemodesParser": GamemodesParser,
    "HeroParser": HeroParser,
    "HeroesParser": HeroesParser,
    "MapsParser": MapsParser,
    "NamecardParser": NamecardParser,
    "PlayerParser": PlayerParser,
    "PlayerStatsSummaryParser": PlayerStatsSummaryParser,
    "RolesParser": RolesParser,
}

# Generic cache manager used in the process
cache_manager = CacheManager()


# Semaphore to limit concurrent requests for async processes
sem = asyncio.Semaphore(settings.max_concurrent_requests)


def get_soon_expired_cache_keys() -> set[str]:
    """Get a set of URIs for values in Parser Cache which are obsolete
    or will need to be updated.
    """
    return set(
        cache_manager.get_soon_expired_cache_keys(settings.parser_cache_key_prefix)
    )


def get_request_parser_class(cache_key: str) -> tuple[type, dict]:
    """Get the request parser class and cache kwargs to use for instanciation"""
    cache_kwargs = {}

    specific_cache_key = cache_key.removeprefix(f"{settings.parser_cache_key_prefix}:")
    parser_class_name = specific_cache_key.split("-")[0]
    cache_parser_class = PARSER_CLASSES_MAPPING[parser_class_name]

    # If the cache is related to local data
    if settings.blizzard_host not in specific_cache_key:
        return cache_parser_class, cache_kwargs

    uri = specific_cache_key.removeprefix(
        f"{parser_class_name}-{settings.blizzard_host}"
    ).split("/")
    cache_kwargs["locale"] = uri[1]
    if parser_class_name in ["PlayerParser", "PlayerStatsSummaryParser"]:
        cache_kwargs["player_id"] = uri[3]
    elif parser_class_name == "NamecardParser":
        cache_kwargs["player_id"] = uri[4].replace("#", "-")
    elif parser_class_name == "HeroParser":
        cache_kwargs["hero_key"] = uri[3]

    return cache_parser_class, cache_kwargs


async def retrieve_data(key: str, parser: AbstractParser):
    """Coroutine for retrieving data for a single parser. We're using a semaphore
    to limit the number of concurrent requests.
    """
    async with sem:
        logger.info("Updating data for {} key...", key)

        try:
            await parser.retrieve_and_parse_data()
        except ParserBlizzardError as error:
            logger.exception(
                "Failed to instanciate Parser when refreshing : {}",
                error.message,
            )
        except ParserParsingError as error:
            overfast_internal_error(parser.blizzard_url, error)
        except HTTPException:
            pass


async def main():
    """Main coroutine of the script"""
    logger.info("Starting Redis cache update...")

    keys_to_update = get_soon_expired_cache_keys()
    logger.info("Done ! Retrieved keys : {}", len(keys_to_update))

    tasks = []
    for key in keys_to_update:
        parser_class, kwargs = get_request_parser_class(key)
        parser = parser_class(**kwargs)
        tasks.append(retrieve_data(key, parser))

    await asyncio.gather(*tasks)

    logger.info("Redis cache update finished !")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="check_and_update_cache"))
    asyncio.run(main())
