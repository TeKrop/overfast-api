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

        Returns dict with 'html', 'summary', 'battletag', 'name',
        'last_updated_blizzard', 'updated_at', 'schema_version' or None if not found
        """
        ...

    async def get_player_id_by_battletag(self, battletag: str) -> str | None:
        """
        Get Blizzard ID (player_id) for a given BattleTag.

        Enables lookup optimization: when user provides a BattleTag we've seen before,
        skip Blizzard redirect and use the cached Blizzard ID directly.

        Returns:
            Blizzard ID if found, None otherwise
        """
        ...

    async def set_player_profile(
        self,
        player_id: str,
        html: str,
        summary: dict | None = None,
        battletag: str | None = None,
        name: str | None = None,
        last_updated_blizzard: int | None = None,
        schema_version: int = 1,
    ) -> None:
        """Store player profile HTML and parsed summary with optional metadata"""
        ...

    async def delete_old_player_profiles(self, max_age_seconds: int) -> int:
        """
        Delete player profiles not updated within max_age_seconds.

        Returns:
            Number of deleted rows
        """
        ...

    async def vacuum(self) -> None:
        """Reclaim disk space by running VACUUM on the database"""
        ...

    async def clear_all_data(self) -> None:
        """Clear all data including static data (for testing)"""
        ...

    async def get_stats(self) -> dict:
        """
        Get storage statistics for monitoring.

        Returns dict with size_bytes, wal_size_bytes, static_data_count,
        player_profiles_count, player_profile_age_p50/p90/p99
        """
        ...

    async def close(self) -> None:
        """Close storage connections"""
        ...
