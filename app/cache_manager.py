"""
Cache manager module, giving simple methods in order to manipulate Valkey cache
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
from typing import TYPE_CHECKING

import valkey

from .config import settings
from .metaclasses import Singleton
from .overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request


class CacheManager(metaclass=Singleton):
    """Cache manager main class, containing methods to retrieve
    and store cache values for both Player and API Cache from Valkey.
    """

    # Valkey server global variable
    valkey_server = valkey.Valkey(
        host=settings.valkey_host, port=settings.valkey_port, protocol=3
    )

    @staticmethod
    def log_warning(err: valkey.exceptions.ValkeyError) -> None:
        logger.warning("Valkey server error : {}", str(err))

    @staticmethod
    def get_cache_key_from_request(request: Request) -> str:
        """Get the cache key associated with a user request"""
        return request.url.path + (
            f"?{request.query_params}" if request.query_params else ""
        )

    @staticmethod
    def __compress_json_value(value: dict | list) -> bytes:
        """Helper method to transform a value into compressed JSON data"""
        return zlib.compress(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def __decompress_json_value(value: bytes) -> dict | list:
        """Helper method to retrieve a value from a compressed JSON data"""
        return json.loads(zlib.decompress(value).decode("utf-8"))

    @staticmethod
    def valkey_connection_handler(func: Callable):
        """Wrapper to handle the Valkey server connection in the Manager methods.
        Errors are logged and the process continues even if Valkey can't be joined.
        """

        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except valkey.exceptions.ValkeyError as err:
                self.log_warning(err)
                return None

        return wrapper

    @valkey_connection_handler
    def get_api_cache(self, cache_key: str) -> dict | list | None:
        """Get the API Cache value associated with a given cache key"""
        api_cache_key = f"{settings.api_cache_key_prefix}:{cache_key}"

        api_cache = self.valkey_server.get(api_cache_key)
        if not api_cache or not isinstance(api_cache, bytes):
            return None

        return self.__decompress_json_value(api_cache)

    @valkey_connection_handler
    def update_api_cache(self, cache_key: str, value: dict | list, expire: int) -> None:
        """Update or set an API Cache value with an expiration value (in seconds)"""

        # Compress the JSON string
        bytes_value = self.__compress_json_value(value)

        # Store it in API Cache
        self.valkey_server.set(
            f"{settings.api_cache_key_prefix}:{cache_key}",
            bytes_value,
            ex=expire,
        )

    @valkey_connection_handler
    def get_player_cache(self, player_id: str) -> dict | list | None:
        """Get the Player Cache value associated with a given cache key"""
        player_key = f"{settings.player_cache_key_prefix}:{player_id}"

        player_cache = self.valkey_server.get(player_key)
        if not player_cache or not isinstance(player_cache, bytes):
            return None

        # Reset the TTL before returning the value
        self.valkey_server.expire(player_key, settings.player_cache_timeout)
        return self.__decompress_json_value(player_cache)

    @valkey_connection_handler
    def update_player_cache(self, player_id: str, value: dict) -> None:
        """Update or set a Player Cache value"""
        compressed_value = self.__compress_json_value(value)
        self.valkey_server.set(
            f"{settings.player_cache_key_prefix}:{player_id}",
            value=compressed_value,
            ex=settings.player_cache_timeout,
        )

    @valkey_connection_handler
    def is_being_rate_limited(self) -> bool:
        return bool(self.valkey_server.exists(settings.blizzard_rate_limit_key))

    @valkey_connection_handler
    def get_global_rate_limit_remaining_time(self) -> int:
        blizzard_rate_limit = self.valkey_server.ttl(settings.blizzard_rate_limit_key)
        return blizzard_rate_limit if isinstance(blizzard_rate_limit, int) else 0

    @valkey_connection_handler
    def set_global_rate_limit(self) -> None:
        self.valkey_server.set(
            settings.blizzard_rate_limit_key,
            value=0,
            ex=settings.blizzard_rate_limit_retry_after,
        )

    @valkey_connection_handler
    def is_player_unknown(self, player_id: str) -> bool:
        return bool(
            self.valkey_server.exists(
                f"{settings.unknown_players_cache_key_prefix}:{player_id}"
            )
        )

    @valkey_connection_handler
    def set_player_as_unknown(self, player_id: str) -> None:
        self.valkey_server.set(
            f"{settings.unknown_players_cache_key_prefix}:{player_id}",
            value=0,
            ex=settings.unknown_players_cache_timeout,
        )
