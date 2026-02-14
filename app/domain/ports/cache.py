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

    async def get_player_cache(self, player_id: str) -> dict | list | None:
        """
        Get the Player Cache value associated with a given player ID.

        Returns decompressed JSON data or None if not found.
        Resets the TTL on successful retrieval.
        """
        ...

    async def update_player_cache(self, player_id: str, value: dict) -> None:
        """
        Update or set a Player Cache value.

        Value is JSON-serialized and compressed before storage.
        Uses configured player cache TTL.
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

    # Unknown player tracking methods
    async def is_player_unknown(self, player_id: str) -> bool:
        """Check if player is marked as unknown"""
        ...

    async def set_player_as_unknown(self, player_id: str) -> None:
        """Mark player as unknown with configured TTL"""
        ...
