"""Cache port protocol for dependency injection"""

from typing import Protocol


class CachePort(Protocol):
    """
    Protocol for cache operations with application-specific methods.

    This protocol defines both low-level cache operations (get/set/delete/exists)
    and high-level application-specific methods for API cache, player cache,
    rate limiting, and unknown player tracking.

    Implementations should use structural typing (duck typing) - no explicit
    inheritance required. Protocol compliance is verified by type checkers.
    """

    # Low-level cache operations
    async def get(self, key: str) -> bytes | None:
        """Get raw value from cache by key"""
        ...

    async def set(
        self,
        key: str,
        value: bytes,
        expire: int | None = None,
    ) -> None:
        """Set raw value in cache with optional expiration (seconds)"""
        ...

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        ...

    # Application-specific cache methods
    async def get_api_cache(self, cache_key: str) -> dict | list | None:
        """
        Get the API Cache value associated with a given cache key.

        Returns decompressed JSON data (dict or list) or None if not found.
        """
        ...

    async def update_api_cache(
        self, cache_key: str, value: dict | list, expire: int
    ) -> None:
        """
        Update or set an API Cache value with an expiration value (in seconds).

        Value is JSON-serialized and compressed before storage.
        """
        ...

    # Rate limiting methods
    async def is_being_rate_limited(self) -> bool:
        """Check if Blizzard rate limit is currently active"""
        ...

    async def get_global_rate_limit_remaining_time(self) -> int:
        """Get remaining time in seconds for Blizzard rate limit"""
        ...

    async def set_global_rate_limit(self) -> None:
        """Set Blizzard rate limit flag with configured TTL"""
        ...

    # Unknown player tracking methods (two-key pattern: cooldown key with TTL + status key permanent)
    async def get_player_status(self, player_id: str) -> dict | None:
        """
        Get unknown player status.

        Checks cooldown:{player_id} key first (active rejection window),
        then falls back to status:{player_id} key (persistent check count).

        Returns dict with 'check_count' and 'retry_after' (remaining seconds, 0 if
        cooldown expired but status persists), or None if player is not tracked.
        """
        ...

    async def set_player_status(
        self,
        player_id: str,
        check_count: int,
        retry_after: int,
        battletag: str | None = None,
    ) -> None:
        """
        Set persistent status key and cooldown keys for an unknown player.

        player_id should be the Blizzard ID (canonical key for status).
        If battletag is provided, an additional cooldown key is set by battletag
        to enable early rejection before identity resolution.
        """
        ...

    async def delete_player_status(self, player_id: str) -> None:
        """Delete status and all associated cooldown keys for player (by Blizzard ID)."""
        ...

    async def evict_volatile_data(self) -> None:
        """
        Delete all Valkey keys except unknown-player status and cooldown keys.

        Called on app shutdown before triggering RDB save so that the snapshot
        contains only persistent unknown-player data.
        """
        ...

    async def bgsave(self) -> None:
        """Trigger a background RDB save (best-effort, errors are logged not raised)."""
        ...
