"""Storage port protocol for persistent data storage"""

from typing import Protocol


class StoragePort(Protocol):
    """
    Protocol for persistent storage operations (SQLite in v4).

    Defines the contract for storage adapters to implement persistent
    caching of static data, player profiles, and unknown player tracking.
    """

    async def initialize(self) -> None:
        """Initialize storage (create tables, setup schema)"""
        ...

    async def get_static_data(self, key: str) -> dict | None:
        """Get static data (heroes, maps, gamemodes, roles, hero_stats) by key"""
        ...

    async def set_static_data(
        self,
        key: str,
        data: str,  # JSON string, not dict (matches implementation)
        data_type: str,
        schema_version: int = 1,
    ) -> None:
        """Store static data with metadata"""
        ...

    async def get_player_profile(self, player_id: str) -> dict | None:
        """
        Get player profile HTML and parsed summary.

        Returns dict with 'html', 'summary', 'blizzard_id', 'last_updated_blizzard',
        'updated_at', 'schema_version' or None if not found
        """
        ...

    async def set_player_profile(
        self,
        player_id: str,
        html: str,
        summary: dict | None = None,
        blizzard_id: str | None = None,
        last_updated_blizzard: int | None = None,
        schema_version: int = 1,
    ) -> None:
        """Store player profile HTML and parsed summary"""
        ...

    async def get_player_status(self, player_id: str) -> dict | None:
        """
        Get player status for unknown player tracking.

        Returns dict with 'check_count', 'last_checked_at', 'retry_after'
        or None if not found
        """
        ...

    async def set_player_status(
        self, player_id: str, check_count: int, retry_after: int
    ) -> None:
        """Set player status for unknown player tracking with exponential backoff"""
        ...

    async def delete_player_status(self, player_id: str) -> None:
        """Delete player status entry"""
        ...

    async def clear_all_data(self) -> None:
        """Clear all data including static data (for testing)"""
        ...

    async def close(self) -> None:
        """Close storage connections"""
        ...
