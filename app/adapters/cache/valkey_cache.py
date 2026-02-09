"""
Valkey cache adapter implementing CachePort.

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

import asyncio
import json
import zlib
from typing import TYPE_CHECKING

import valkey

from app.config import settings
from app.metaclasses import Singleton
from app.overfast_logger import logger

if TYPE_CHECKING:
    from fastapi import Request


class ValkeyCache(metaclass=Singleton):
    """
    Valkey cache adapter implementing CachePort protocol.

    Implements CachePort protocol via structural typing (duck typing).
    Protocol compliance is verified by type checkers at injection points.
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
    def _compress_json_value(value: dict | list) -> bytes:
        """Helper method to transform a value into compressed JSON data"""
        return zlib.compress(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def _decompress_json_value(value: bytes) -> dict | list:
        """Helper method to retrieve a value from a compressed JSON data"""
        return json.loads(zlib.decompress(value).decode("utf-8"))

    def _handle_valkey_error(self, func):
        """Helper to handle Valkey connection errors"""
        try:
            return func()
        except valkey.exceptions.ValkeyError as err:
            self.log_warning(err)
            return None

    # CachePort protocol methods
    async def get(self, key: str) -> bytes | None:
        """Get raw value from cache by key"""

        def _get():
            value = self.valkey_server.get(key)
            return value if isinstance(value, bytes) else None

        return await asyncio.to_thread(lambda: self._handle_valkey_error(_get))

    async def set(
        self,
        key: str,
        value: bytes,
        expire: int | None = None,
    ) -> None:
        """Set raw value in cache with optional expiration (seconds)"""

        def _set():
            self.valkey_server.set(key, value, ex=expire)

        await asyncio.to_thread(lambda: self._handle_valkey_error(_set))

    async def delete(self, key: str) -> None:
        """Delete key from cache"""

        def _delete():
            self.valkey_server.delete(key)

        await asyncio.to_thread(lambda: self._handle_valkey_error(_delete))

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""

        def _exists():
            return bool(self.valkey_server.exists(key))

        result = await asyncio.to_thread(lambda: self._handle_valkey_error(_exists))
        return result or False

    # Legacy application-specific methods (kept for backward compatibility during migration)
    def get_api_cache(self, cache_key: str) -> dict | list | None:
        """Get the API Cache value associated with a given cache key"""

        def _get_api_cache():
            api_cache_key = f"{settings.api_cache_key_prefix}:{cache_key}"
            api_cache = self.valkey_server.get(api_cache_key)
            if not api_cache or not isinstance(api_cache, bytes):
                return None
            return self._decompress_json_value(api_cache)

        return self._handle_valkey_error(_get_api_cache)

    def update_api_cache(self, cache_key: str, value: dict | list, expire: int) -> None:
        """Update or set an API Cache value with an expiration value (in seconds)"""

        def _update_api_cache():
            bytes_value = self._compress_json_value(value)
            self.valkey_server.set(
                f"{settings.api_cache_key_prefix}:{cache_key}",
                bytes_value,
                ex=expire,
            )

        self._handle_valkey_error(_update_api_cache)

    def get_player_cache(self, player_id: str) -> dict | list | None:
        """Get the Player Cache value associated with a given cache key"""

        def _get_player_cache():
            player_key = f"{settings.player_cache_key_prefix}:{player_id}"
            player_cache = self.valkey_server.get(player_key)
            if not player_cache or not isinstance(player_cache, bytes):
                return None
            # Reset the TTL before returning the value
            self.valkey_server.expire(player_key, settings.player_cache_timeout)
            return self._decompress_json_value(player_cache)

        return self._handle_valkey_error(_get_player_cache)

    def update_player_cache(self, player_id: str, value: dict) -> None:
        """Update or set a Player Cache value"""

        def _update_player_cache():
            compressed_value = self._compress_json_value(value)
            self.valkey_server.set(
                f"{settings.player_cache_key_prefix}:{player_id}",
                value=compressed_value,
                ex=settings.player_cache_timeout,
            )

        self._handle_valkey_error(_update_player_cache)

    def is_being_rate_limited(self) -> bool:
        def _is_rate_limited():
            return bool(self.valkey_server.exists(settings.blizzard_rate_limit_key))

        return self._handle_valkey_error(_is_rate_limited) or False

    def get_global_rate_limit_remaining_time(self) -> int:
        def _get_remaining_time():
            blizzard_rate_limit = self.valkey_server.ttl(
                settings.blizzard_rate_limit_key
            )
            return blizzard_rate_limit if isinstance(blizzard_rate_limit, int) else 0

        return self._handle_valkey_error(_get_remaining_time) or 0

    def set_global_rate_limit(self) -> None:
        def _set_rate_limit():
            self.valkey_server.set(
                settings.blizzard_rate_limit_key,
                value=0,
                ex=settings.blizzard_rate_limit_retry_after,
            )

        self._handle_valkey_error(_set_rate_limit)

    def is_player_unknown(self, player_id: str) -> bool:
        def _is_unknown():
            return bool(
                self.valkey_server.exists(
                    f"{settings.unknown_players_cache_key_prefix}:{player_id}"
                )
            )

        return self._handle_valkey_error(_is_unknown) or False

    def set_player_as_unknown(self, player_id: str) -> None:
        def _set_unknown():
            self.valkey_server.set(
                f"{settings.unknown_players_cache_key_prefix}:{player_id}",
                value=0,
                ex=settings.unknown_players_cache_timeout,
            )

        self._handle_valkey_error(_set_unknown)


# Backward compatibility alias
CacheManager = ValkeyCache
