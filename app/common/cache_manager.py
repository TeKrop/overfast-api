"""
Cache manager module, giving simple methods in order to manipulate Redis cache
specifically for this application.

API Cache will expire depending on the given route. It simply contains
a string representing the processed JSON to return. It's used by nginx
reverse-proxy before calling the application server.

Examples :
api-cache:/heroes => "[{...}]"
api-cache:/heroes?role=damage => "[{...}]"

----

Parser Cache data will never expire and just be invalidated using MD5 hash check.
It simply contains a JSON string representation of parsed data of a given Blizzard
HTML page. MD5 hash is calculated using the HTML ready to be parsed
(only the part used for parsing).

Examples :
parser-cache:https://overwatch.blizzard.com/en-us/heroes
=> {"hash": "12345abcdef", "data": "[{...}]"}
parser-cache:https://overwatch.blizzard.com/en-us/heroes/ana
=> {"hash": "12345abcdef", "data": "[{...}]"}
"""

import json
from collections.abc import Callable, Iterator

import redis
from fastapi import Request

from app.config import settings

from .helpers import compress_json_value, decompress_json_value
from .logging import logger
from .metaclasses import Singleton


class CacheManager(metaclass=Singleton):
    """Cache manager main class, containing methods to retrieve
    and store cache values for both Parser and API Cache from Redis.
    """

    # Redis server global variable
    redis_server = (
        redis.Redis(host=settings.redis_host, port=settings.redis_port)
        if settings.redis_caching_enabled
        else None
    )

    # Whenever we encounter an error on Redis connection, this variable is set
    # to False to prevent trying to reach the Redis server multiple times.
    is_redis_server_up = settings.redis_caching_enabled

    @staticmethod
    def get_cache_key_from_request(request: Request) -> str:
        """Get the cache key associated with a user request"""
        return request.url.path + (
            f"?{request.query_params}" if request.query_params else ""
        )

    @staticmethod
    def redis_connection_handler(func: Callable):
        """Wrapper to handle the Redis server connection in the Manager methods.
        Errors are logged and the process continues even if Redis can't be joined.
        """

        def wrapper(self, *args, **kwargs):
            if not self.is_redis_server_up:
                return None
            try:
                return func(self, *args, **kwargs)
            except redis.exceptions.RedisError as err:
                logger.warning("Redis server error : {}", str(err))
                return None

        return wrapper

    @redis_connection_handler
    def get_api_cache(self, cache_key: str) -> str | None:
        """Get the API Cache value associated with a given cache key"""
        return self.redis_server.get(f"{settings.api_cache_key_prefix}:{cache_key}")

    @redis_connection_handler
    def get_parser_cache(self, cache_key: str) -> dict | list | None:
        """Get the Parser Cache value associated with a given cache key"""
        parser_cache = self.redis_server.get(
            f"{settings.parser_cache_key_prefix}:{cache_key}"
        )
        return decompress_json_value(parser_cache) if parser_cache else None

    @redis_connection_handler
    def update_api_cache(self, cache_key: str, value: dict | list, expire: int) -> None:
        """Update or set an API Cache value with an expiration value (in seconds)"""

        # Compress the JSON string
        str_value = json.dumps(value, separators=(",", ":"))

        # Store it in API Cache
        self.redis_server.set(
            f"{settings.api_cache_key_prefix}:{cache_key}", str_value, ex=expire
        )

    @redis_connection_handler
    def update_parser_cache(self, cache_key: str, value: dict, expire: int) -> None:
        """Update or set a Parser Cache value with an expire value"""
        compressed_value = compress_json_value(value)

        self.redis_server.set(
            f"{settings.parser_cache_key_prefix}:{cache_key}",
            value=compressed_value,
            ex=expire,
        )

    def get_soon_expired_cache_keys(self, cache_key_prefix: str) -> Iterator[str]:
        """Get a set of cache keys for values in cache which will expire soon, meaning
        the associated TTL is close to expiration."""
        if not self.is_redis_server_up:
            yield from ()
            return

        try:
            cache_keys = self.redis_server.keys(pattern=f"{cache_key_prefix}:*")
        except redis.exceptions.RedisError as err:
            logger.warning("Redis server error : {}", str(err))
            yield from ()
            return

        for key in cache_keys:
            # Get key TTL in redis
            try:
                key_ttl = self.redis_server.ttl(key)
            except redis.exceptions.RedisError as err:
                logger.warning("Redis server error : {}", str(err))
                continue

            # If the key doesn't have any TTL or the limit is far, we don't do anything
            if key_ttl < 0 or key_ttl > settings.expired_cache_refresh_limit:
                continue

            yield key.decode("utf-8")

    @redis_connection_handler
    def update_namecards_cache(self, namecards: dict[str, str]) -> None:
        for namecard_key, namecard_url in namecards.items():
            self.redis_server.set(
                f"{settings.namecard_cache_key_prefix}:{namecard_key}",
                value=namecard_url,
                ex=settings.namecards_timeout,
            )

    @redis_connection_handler
    def get_namecard_cache(self, cache_key: str) -> str | None:
        namecard_cache = self.redis_server.get(
            f"{settings.namecard_cache_key_prefix}:{cache_key}"
        )
        return namecard_cache.decode("utf-8") if namecard_cache else None

    @redis_connection_handler
    def update_parser_cache_last_update(self, cache_key: str, expire: int) -> None:
        self.redis_server.set(
            f"{settings.parser_cache_last_update_key_prefix}:{cache_key}",
            value=0,
            ex=expire,
        )

    @redis_connection_handler
    def delete_keys(self, keys: list[str]) -> None:
        self.redis_server.delete(keys)
