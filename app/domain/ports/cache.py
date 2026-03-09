"""Cache port protocol for dependency injection"""

from typing import Protocol


class CachePort(Protocol):
    """
    Protocol for cache operations.

    This protocol defines both low-level cache operations (get/set/delete/exists)
    and high-level application-specific methods for API cache management and
    unknown player tracking.

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
        Get the API cache value associated with a given cache key.

        Returns decompressed JSON data (dict or list) or None if not found.
        """
        ...

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
        """Update or set an API cache value with an expiration (in seconds).

        Value is wrapped in a metadata envelope before storage::

            {"data_json": "<pre-serialized JSON string>",
             "stored_at": <unix epoch>,
             "staleness_threshold": <seconds>,
             "stale_while_revalidate": <seconds>}

        Args:
            cache_key: Cache key suffix.
            value: Data payload to cache.
            expire: Key TTL in seconds.
            stored_at: Unix timestamp when the data was generated. Defaults to now.
            staleness_threshold: Seconds after which the payload is considered stale.
                Defaults to ``expire``.
            stale_while_revalidate: Seconds the caller may serve stale data while
                revalidating. 0 means no SWR window.
        """
        ...

    # Unknown player tracking methods
    async def get_player_status(self, player_id: str) -> dict | None:
        """
        Get the tracking status for an unknown player.

        Returns a dict with 'check_count' and 'retry_after' (remaining seconds,
        0 if the active window expired but the record persists), or None if the
        player is not tracked.
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
        Record or update the tracking status for an unknown player.

        player_id is the canonical identifier. If battletag is provided, an
        additional short-lived entry is stored by battletag to allow early
        rejection before full identity resolution.
        """
        ...

    async def delete_player_status(self, player_id: str) -> None:
        """Delete the tracking status and all associated entries for a player."""
        ...

    async def scan_keys(self, pattern: str) -> list[str]:
        """Return all cache keys matching the given glob pattern.

        Uses non-blocking iteration. Returns an empty list if no keys match
        or on error.
        """
        ...

    async def evict_volatile_data(self) -> None:
        """
        Delete all volatile (short-lived) cache entries, preserving persistent ones.

        Called on startup and shutdown to ensure the persisted cache state
        contains only durable data.
        """
        ...

    async def evict_low_count_player_statuses(self) -> None:
        """Delete player status entries whose check_count is strictly below the
        configured minimum retention count, along with their associated entries.

        Called on shutdown after evict_volatile_data() so that low-signal entries
        are not persisted. Set the minimum retention count to 0 to disable.
        """
        ...

    async def bgsave(self) -> None:
        """Persist the current cache state to durable storage (best-effort)."""
        ...
