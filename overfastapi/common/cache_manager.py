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
import zlib
from typing import Callable, Iterator

import redis
from fastapi import Request

from overfastapi.common.logging import logger
from overfastapi.common.metaclasses import Singleton
from overfastapi.config import (
    API_CACHE_KEY_PREFIX,
    EXPIRED_CACHE_REFRESH_LIMIT,
    PARSER_CACHE_KEY_PREFIX,
    REDIS_CACHING_ENABLED,
    REDIS_HOST,
    REDIS_PORT,
)


class CacheManager(metaclass=Singleton):
    """Cache manager main class, containing methods to retrieve
    and store cache values for both Parser and API Cache from Redis.
    """

    # Redis server global variable
    redis_server = (
        redis.Redis(host=REDIS_HOST, port=REDIS_PORT) if REDIS_CACHING_ENABLED else None
    )

    # Whenever we encounter an error on Redis connection, this variable is set
    # to False to prevent trying to reach the Redis server multiple times.
    is_redis_server_up = REDIS_CACHING_ENABLED

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
        return self.redis_server.get(f"{API_CACHE_KEY_PREFIX}:{cache_key}")

    @redis_connection_handler
    def get_parser_cache(self, cache_key: str) -> dict | None:
        """Get the Parser Cache value associated with a given cache key"""
        parser_cache = self.redis_server.get(f"{PARSER_CACHE_KEY_PREFIX}:{cache_key}")
        return (
            json.loads(zlib.decompress(parser_cache).decode("utf-8"))
            if parser_cache
            else None
        )

    @redis_connection_handler
    def update_api_cache(self, cache_key: str, value: dict | list, expire: int) -> None:
        """Update or set an API Cache value with an expiration value (in seconds)"""

        # Compress the JSON string
        str_value = json.dumps(value, separators=(",", ":"))

        # Store it in API Cache
        self.redis_server.set(
            f"{API_CACHE_KEY_PREFIX}:{cache_key}", str_value, ex=expire
        )

    @redis_connection_handler
    def update_parser_cache(self, cache_key: str, value: dict, expire: int) -> None:
        """Update or set a Parser Cache value with an expire value"""
        compressed_value = zlib.compress(
            json.dumps(value, separators=(",", ":")).encode("utf-8")
        )
        self.redis_server.set(
            f"{PARSER_CACHE_KEY_PREFIX}:{cache_key}", value=compressed_value, ex=expire
        )

    def get_soon_expired_parser_cache_keys(self) -> Iterator[str]:
        """Get a set of cache keys for values in Parser Cache which will expire soon"""
        if not self.is_redis_server_up:
            yield from ()
            return

        try:
            parser_cache_keys = self.redis_server.keys(
                pattern=f"{PARSER_CACHE_KEY_PREFIX}:*"
            )
        except redis.exceptions.RedisError as err:
            logger.warning("Redis server error : {}", str(err))
            yield from ()
            return

        for key in parser_cache_keys:
            # Get key TTL in redis
            try:
                key_ttl = self.redis_server.ttl(key)
            except redis.exceptions.RedisError as err:
                logger.warning("Redis server error : {}", str(err))
                continue

            # If the key doesn't have any TTL or the limit is far, we don't do anything
            if key_ttl < 0 or key_ttl > EXPIRED_CACHE_REFRESH_LIMIT:
                continue

            yield key.decode("utf-8")
