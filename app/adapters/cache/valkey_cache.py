"""
Valkey cache adapter implementing CachePort.

API Cache will expire depending on the given route. It simply contains
a string representing the processed JSON to return. It's used by nginx
reverse-proxy before calling the application server.

Examples :
api-cache:/heroes => "[{...}]"
api-cache:/heroes?role=damage => "[{...}]"

----

Unknown Player Cache uses a two-key pattern per player:
- unknown-player:cooldown:{id}  TTL=retry_after, value=check_count  (fast rejection gate)
- unknown-player:status:{id}    no TTL, value=JSON{check_count,battletag}  (persistent backoff state)

The cooldown key drives rejection; the status key preserves check_count across
cooldown expirations so exponential backoff keeps growing.
"""

import json
import time
from compression import zstd
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

    def __init__(self) -> None:
        # Create the Valkey client lazily so it binds to the running event loop
        self.valkey_server = valkey.Valkey(
            host=settings.valkey_host, port=settings.valkey_port, protocol=3
        )

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
        # Use module-level function for better performance
        return zstd.compress(json_str.encode("utf-8"))

    @staticmethod
    def _decompress_json_value(value: bytes) -> dict | list:
        """Helper method to retrieve a value from a compressed JSON data using zstd"""
        # Use module-level function for better performance
        return json.loads(zstd.decompress(value).decode("utf-8"))

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
        """Get the API Cache value associated with a given cache key."""
        api_cache_key = f"{settings.api_cache_key_prefix}:{cache_key}"
        api_cache = await self.valkey_server.get(api_cache_key)
        if not api_cache or not isinstance(api_cache, bytes):
            return None
        envelope = self._decompress_json_value(api_cache)
        if isinstance(envelope, dict) and "data_json" in envelope:
            return json.loads(envelope["data_json"])
        return envelope

    @handle_valkey_error(default_return=None)
    async def update_api_cache(
        self,
        cache_key: str,
        value: dict | list,
        expire: int,
        *,
        stored_at: int | None = None,
        staleness_threshold: int | None = None,
        stale_while_revalidate: int = 0,
    ) -> None:
        """Wrap value in a metadata envelope, compress, and store with TTL.

        ``data_json`` is the pre-serialized JSON string (key order preserved by
        Python's ``json.dumps``), so nginx/Lua can print it verbatim without
        re-encoding through cjson (which does not guarantee key ordering).
        """
        envelope: dict = {
            "data_json": json.dumps(value, separators=(",", ":")),
            "stored_at": stored_at if stored_at is not None else int(time.time()),
            "staleness_threshold": (
                staleness_threshold if staleness_threshold is not None else expire
            ),
            "stale_while_revalidate": stale_while_revalidate,
        }
        bytes_value = self._compress_json_value(envelope)
        await self.valkey_server.set(
            f"{settings.api_cache_key_prefix}:{cache_key}",
            bytes_value,
            ex=expire,
        )

    @handle_valkey_error(default_return=None)
    async def get_player_status(self, player_id: str) -> dict | None:
        """
        Get unknown player status by battletag or Blizzard ID.

        Checks cooldown:{player_id} first (TTL-based active window), then falls back
        to status:{player_id} (permanent record). Returns None if not tracked.
        """
        cooldown_key = f"{settings.unknown_player_cooldown_key_prefix}:{player_id}"
        status_key = f"{settings.unknown_player_status_key_prefix}:{player_id}"

        async with self.valkey_server.pipeline(transaction=False) as pipe:
            pipe.get(cooldown_key)
            pipe.ttl(cooldown_key)
            pipe.get(status_key)
            check_count_bytes, remaining_ttl, status_bytes = await pipe.execute()

        if check_count_bytes is not None and remaining_ttl > 0:
            return {"check_count": int(check_count_bytes), "retry_after": remaining_ttl}

        if status_bytes is not None:
            status = json.loads(status_bytes)
            return {
                "check_count": status["check_count"],
                "retry_after": 0,
                "battletag": status.get("battletag"),
            }

        return None

    @handle_valkey_error(default_return=None)
    async def set_player_status(
        self,
        player_id: str,
        check_count: int,
        retry_after: int,
        battletag: str | None = None,
    ) -> None:
        """Set persistent status key and TTL-based cooldown keys for an unknown player."""
        status_value = json.dumps({"check_count": check_count, "battletag": battletag})

        async with self.valkey_server.pipeline(transaction=False) as pipe:
            pipe.set(
                f"{settings.unknown_player_status_key_prefix}:{player_id}", status_value
            )
            pipe.set(
                f"{settings.unknown_player_cooldown_key_prefix}:{player_id}",
                check_count,
                ex=retry_after,
            )
            if battletag:
                pipe.set(
                    f"{settings.unknown_player_cooldown_key_prefix}:{battletag}",
                    check_count,
                    ex=retry_after,
                )
            await pipe.execute()

    @handle_valkey_error(default_return=None)
    async def delete_player_status(self, player_id: str) -> None:
        """Delete status and all associated cooldown keys for a player (by Blizzard ID)."""
        status_key = f"{settings.unknown_player_status_key_prefix}:{player_id}"

        # Read battletag from status to also delete the battletag-based cooldown key
        status_bytes = await self.valkey_server.get(status_key)
        battletag = json.loads(status_bytes).get("battletag") if status_bytes else None

        keys_to_delete = [
            status_key,
            f"{settings.unknown_player_cooldown_key_prefix}:{player_id}",
        ]
        if battletag:
            keys_to_delete.append(
                f"{settings.unknown_player_cooldown_key_prefix}:{battletag}"
            )
        await self.valkey_server.delete(*keys_to_delete)

    @handle_valkey_error(default_return=None)
    async def evict_volatile_data(self) -> None:
        """Delete all Valkey keys except unknown-player status and cooldown keys."""
        _evict_batch_size = 1000
        prefixes_to_keep = (
            settings.unknown_player_cooldown_key_prefix,
            settings.unknown_player_status_key_prefix,
        )
        keys_to_delete = []
        async for key in self.valkey_server.scan_iter(
            match="*", count=_evict_batch_size
        ):
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            if not key_str.startswith(prefixes_to_keep):
                keys_to_delete.append(key)
                if len(keys_to_delete) >= _evict_batch_size:
                    await self.valkey_server.delete(*keys_to_delete)
                    keys_to_delete.clear()
        if keys_to_delete:
            await self.valkey_server.delete(*keys_to_delete)
        logger.info("Evicted volatile Valkey keys before shutdown")

    @handle_valkey_error(default_return=None)
    async def bgsave(self) -> None:
        """Trigger a background RDB save."""
        await self.valkey_server.bgsave()
        logger.info("Valkey BGSAVE triggered")


# Backward compatibility alias
CacheManager = ValkeyCache
