"""Storage port protocol for persistent data storage"""

from enum import StrEnum
from typing import Protocol


class StaticDataCategory(StrEnum):
    """Category of static data stored in persistent storage."""

    HEROES = "heroes"
    HERO = "hero"
    GAMEMODES = "gamemodes"
    MAPS = "maps"
    ROLES = "roles"


class StoragePort(Protocol):
    """Protocol for persistent storage operations.

    Defines the contract for storage adapters to implement persistent
    caching of static data and player profiles.
    """

    async def initialize(self) -> None:
        """Initialize storage (create tables, setup schema)"""
        ...

    async def get_static_data(self, key: str) -> dict | None:
        """Get static data (heroes, maps, gamemodes, roles) by key.

        Returns dict with 'data' (str — raw HTML or JSON), 'category' (str),
        'updated_at' (int Unix ts), 'data_version' (int) or None if not found.
        """
        ...

    async def set_static_data(
        self,
        key: str,
        data: str,
        category: StaticDataCategory,
        data_version: int = 1,
    ) -> None:
        """Store static data. ``data`` is a raw string (HTML or JSON)."""
        ...

    async def get_player_profile(self, player_id: str) -> dict | None:
        """
        Get player profile HTML and parsed summary.

        Returns dict with 'html', 'summary' (dict), 'battletag', 'name',
        'last_updated_blizzard', 'updated_at' (int Unix ts), 'data_version'
        or None if not found.
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
        data_version: int = 1,
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

    async def clear_all_data(self) -> None:
        """Clear all data including static data (for testing)"""
        ...

    async def get_stats(self) -> dict:
        """
        Get storage statistics for monitoring.

        Returns dict with size_bytes, static_data_count,
        player_profiles_count, player_profile_age_p50/p90/p99.
        """
        ...

    async def close(self) -> None:
        """Close storage connections"""
        ...
