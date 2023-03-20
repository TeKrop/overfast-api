"""Command used in order to delete Parser Cache which hasn't been retrieved
from API since a certain amount of time. It can be run in the background.
"""
from app.common.cache_manager import CacheManager
from app.common.logging import logger
from app.config import settings

# Generic cache manager used in the process
cache_manager = CacheManager()


def get_soon_expired_cache_keys() -> set[str]:
    """Get a set of keys for values in Parser Cache which should be deleted"""
    return set(
        cache_manager.get_soon_expired_cache_keys(
            settings.parser_cache_last_update_key_prefix
        )
    )


def delete_parser_cache_keys(parser_keys: set[str]) -> None:
    """Delete all Parser Cache related keys : the ones prefixed for the
    Parser Cache data, and the ones used and retrieved in this process.
    """
    cache_manager.delete_keys(
        f"{prefix}:{key}"
        for key in parser_keys
        for prefix in [
            settings.parser_cache_key_prefix,
            settings.parser_cache_last_update_key_prefix,
        ]
    )


def main():
    """Main function of the script"""
    logger.info("Starting Parser Cache expiration system...")
    parser_keys = get_soon_expired_cache_keys()
    logger.info("Parser keys retrieval done !")
    if not parser_keys:
        logger.info("No Parser key to delete, closing")
        raise SystemExit

    logger.info("Deleting {} keys from Redis...", len(parser_keys))
    delete_parser_cache_keys(parser_keys)
    logger.info("Parser Cache cleaning done !")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(
        lambda record: record.update(name="check_and_delete_parser_cache")
    )
    main()
