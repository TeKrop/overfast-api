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

import json
from compression.zstd import ZstdCompressor, ZstdDecompressor
from functools import wraps
from typing import TYPE_CHECKING, Any

import valkey.asyncio as valkey

from app.config import settings
from app.metaclasses import Singleton
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request


def handle_valkey_error(
    default_return: Any = None,
) -> Callable[[Callable], Callable]:
    """
    Decorator to handle Valkey connection errors gracefully.

    Args:
        default_return: Value to return when ValkeyError is caught (default: None)

    Returns:
        Decorated async function that catches ValkeyError and returns default_return
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except valkey.ValkeyError as err:
                func_name = getattr(func, "__name__", "unknown")
                logger.warning(f"Valkey server error in {func_name}: {err}")
                return default_return

        return wrapper

    return decorator


class ValkeyCache(metaclass=Singleton):
    """
    Async Valkey cache adapter implementing CachePort protocol.

    All methods are async for non-blocking I/O.
    Protocol compliance is verified by type checkers at injection points.
    """

    # Valkey server global variable (async client)
    valkey_server = valkey.Valkey(
        host=settings.valkey_host, port=settings.valkey_port, protocol=3
    )

    # zstd compressor/decompressor (Python 3.14+)
    _compressor = ZstdCompressor()
    _decompressor = ZstdDecompressor()

    @staticmethod
    def get_cache_key_from_request(request: Request) -> str:
        """Get the cache key associated with a user request"""
        return request.url.path + (
            f"?{request.query_params}" if request.query_params else ""
        )

    @staticmethod
    def _compress_json_value(value: dict | list) -> bytes:
        """Helper method to transform a value into compressed JSON data using zstd"""
        json_str = json.dumps(value, separators=(",", ":"))
        # Use FLUSH_FRAME mode to ensure complete compression
        return ValkeyCache._compressor.compress(
            json_str.encode("utf-8"), ValkeyCache._compressor.FLUSH_FRAME
        )

    @staticmethod
    def _decompress_json_value(value: bytes) -> dict | list:
        """Helper method to retrieve a value from a compressed JSON data using zstd"""
        return json.loads(ValkeyCache._decompressor.decompress(value).decode("utf-8"))

    # CachePort protocol methods
    @handle_valkey_error(default_return=None)
    async def get(self, key: str) -> bytes | None:
        """Get raw value from cache by key"""
        value = await self.valkey_server.get(key)
        return value if isinstance(value, bytes) else None

    @handle_valkey_error(default_return=None)
    async def set(
        self,
        key: str,
        value: bytes,
        expire: int | None = None,
    ) -> None:
        """Set raw value in cache with optional expiration (seconds)"""
        await self.valkey_server.set(key, value, ex=expire)

    @handle_valkey_error(default_return=None)
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        await self.valkey_server.delete(key)

    @handle_valkey_error(default_return=False)
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        result = await self.valkey_server.exists(key)
        return bool(result)

    # Application-specific cache methods
    @handle_valkey_error(default_return=None)
    async def get_api_cache(self, cache_key: str) -> dict | list | None:
        """Get the API Cache value associated with a given cache key"""
        api_cache_key = f"{settings.api_cache_key_prefix}:{cache_key}"
        api_cache = await self.valkey_server.get(api_cache_key)
        if not api_cache or not isinstance(api_cache, bytes):
            return None
        return self._decompress_json_value(api_cache)

    @handle_valkey_error(default_return=None)
    async def update_api_cache(
        self, cache_key: str, value: dict | list, expire: int
    ) -> None:
        """Update or set an API Cache value with an expiration value (in seconds)"""
        bytes_value = self._compress_json_value(value)
        await self.valkey_server.set(
            f"{settings.api_cache_key_prefix}:{cache_key}",
            bytes_value,
            ex=expire,
        )

    @handle_valkey_error(default_return=None)
    async def get_player_cache(self, player_id: str) -> dict | list | None:
        """Get the Player Cache value associated with a given cache key"""
        player_key = f"{settings.player_cache_key_prefix}:{player_id}"
        player_cache = await self.valkey_server.get(player_key)
        if not player_cache or not isinstance(player_cache, bytes):
            return None
        # Reset the TTL before returning the value
        await self.valkey_server.expire(player_key, settings.player_cache_timeout)
        return self._decompress_json_value(player_cache)

    @handle_valkey_error(default_return=None)
    async def update_player_cache(self, player_id: str, value: dict) -> None:
        """Update or set a Player Cache value"""
        compressed_value = self._compress_json_value(value)
        await self.valkey_server.set(
            f"{settings.player_cache_key_prefix}:{player_id}",
            value=compressed_value,
            ex=settings.player_cache_timeout,
        )

    @handle_valkey_error(default_return=False)
    async def is_being_rate_limited(self) -> bool:
        """Check if Blizzard rate limit is currently active"""
        result = await self.valkey_server.exists(settings.blizzard_rate_limit_key)
        return bool(result)

    @handle_valkey_error(default_return=0)
    async def get_global_rate_limit_remaining_time(self) -> int:
        """Get remaining time in seconds for Blizzard rate limit"""
        blizzard_rate_limit = await self.valkey_server.ttl(
            settings.blizzard_rate_limit_key
        )
        return blizzard_rate_limit if isinstance(blizzard_rate_limit, int) else 0

    @handle_valkey_error(default_return=None)
    async def set_global_rate_limit(self) -> None:
        """Set Blizzard rate limit flag"""
        await self.valkey_server.set(
            settings.blizzard_rate_limit_key,
            value=0,
            ex=settings.blizzard_rate_limit_retry_after,
        )

    @handle_valkey_error(default_return=False)
    async def is_player_unknown(self, player_id: str) -> bool:
        """Check if player is marked as unknown"""
        result = await self.valkey_server.exists(
            f"{settings.unknown_players_cache_key_prefix}:{player_id}"
        )
        return bool(result)

    @handle_valkey_error(default_return=None)
    async def set_player_as_unknown(self, player_id: str) -> None:
        """Mark player as unknown"""
        await self.valkey_server.set(
            f"{settings.unknown_players_cache_key_prefix}:{player_id}",
            value=0,
            ex=settings.unknown_players_cache_timeout,
        )


# Backward compatibility alias
CacheManager = ValkeyCache
