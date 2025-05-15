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

Player Cache data will not expire. It's JSON containing data from
players search page and HTML data from Blizzard profile page.

Examples :
player-cache:TeKrop-2217
=> {"summary": {"...": "...""}, "profile": "<html>....</html>"}
"""

import json
import zlib
from collections.abc import Callable

import redis
from fastapi import Request

from .config import settings
from .metaclasses import Singleton
from .overfast_logger import logger


class CacheManager(metaclass=Singleton):
    """Cache manager main class, containing methods to retrieve
    and store cache values for both Player and API Cache from Redis.
    """

    # Redis server global variable
    redis_server = redis.Redis(host=settings.redis_host, port=settings.redis_port)

    @staticmethod
    def log_warning(err: redis.exceptions.RedisError) -> None:
        logger.warning("Redis server error : {}", str(err))

    @staticmethod
    def get_cache_key_from_request(request: Request) -> str:
        """Get the cache key associated with a user request"""
        return request.url.path + (
            f"?{request.query_params}" if request.query_params else ""
        )

    @staticmethod
    def __compress_json_value(value: dict | list) -> str:
        """Helper method to transform a value into compressed JSON data"""
        return zlib.compress(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def __decompress_json_value(value: str) -> dict | list:
        """Helper method to retrieve a value from a compressed JSON data"""
        return json.loads(zlib.decompress(value).decode("utf-8"))

    @staticmethod
    def redis_connection_handler(func: Callable):
        """Wrapper to handle the Redis server connection in the Manager methods.
        Errors are logged and the process continues even if Redis can't be joined.
        """

        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except redis.exceptions.RedisError as err:
                self.log_warning(err)
                return None

        return wrapper

    @redis_connection_handler
    def get_api_cache(self, cache_key: str) -> dict | list | None:
        """Get the API Cache value associated with a given cache key"""
        api_cache_key = f"{settings.api_cache_key_prefix}:{cache_key}"
        if not (api_cache := self.redis_server.get(api_cache_key)):
            return None

        return self.__decompress_json_value(api_cache)

    @redis_connection_handler
    def update_api_cache(self, cache_key: str, value: dict | list, expire: int) -> None:
        """Update or set an API Cache value with an expiration value (in seconds)"""

        # Compress the JSON string
        str_value = self.__compress_json_value(value)

        # Store it in API Cache
        self.redis_server.set(
            f"{settings.api_cache_key_prefix}:{cache_key}",
            str_value,
            ex=expire,
        )

    @redis_connection_handler
    def get_player_cache(self, player_id: str) -> dict | list | None:
        """Get the Player Cache value associated with a given cache key"""
        player_key = f"{settings.player_cache_key_prefix}:{player_id}"
        if not (player_cache := self.redis_server.get(player_key)):
            return None

        # Reset the TTL before returning the value
        self.redis_server.expire(player_key, settings.player_cache_timeout)
        return self.__decompress_json_value(player_cache)

    @redis_connection_handler
    def update_player_cache(self, player_id: str, value: dict) -> None:
        """Update or set a Player Cache value"""
        compressed_value = self.__compress_json_value(value)
        self.redis_server.set(
            f"{settings.player_cache_key_prefix}:{player_id}",
            value=compressed_value,
            ex=settings.player_cache_timeout,
        )

    @redis_connection_handler
    def get_unlock_data_cache(self, cache_key: str) -> str | None:
        data_cache = self.redis_server.hget(settings.unlock_data_cache_key, cache_key)
        return data_cache.decode("utf-8") if data_cache else None

    @redis_connection_handler
    def update_unlock_data_cache(self, unlock_data: dict[str, str]) -> None:
        for data_key, data_value in unlock_data.items():
            self.redis_server.hset(
                settings.unlock_data_cache_key,
                data_key,
                data_value,
            )

    @redis_connection_handler
    def is_being_rate_limited(self) -> bool:
        return self.redis_server.exists(settings.blizzard_rate_limit_key)

    @redis_connection_handler
    def get_global_rate_limit_remaining_time(self) -> int:
        return self.redis_server.ttl(settings.blizzard_rate_limit_key)

    @redis_connection_handler
    def set_global_rate_limit(self) -> None:
        self.redis_server.set(
            settings.blizzard_rate_limit_key,
            value=0,
            ex=settings.blizzard_rate_limit_retry_after,
        )
