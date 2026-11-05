"""Storage port protocol for persistent data storage"""

from enum import StrEnum
from typing import Protocol, TypedDict


class StaticDataCategory(StrEnum):
    """Category of static data stored in persistent storage."""

    HEROES = "heroes"
    HERO = "hero"
    GAMEMODES = "gamemodes"
    MAPS = "maps"
    ROLES = "roles"


class StoredStaticData(TypedDict):
    """Static data row as returned by ``get_static_data``."""

    data: str
    category: str
    updated_at: int
    data_version: int


class StoredPlayerProfile(TypedDict):
    """Player profile row as returned by ``get_player_profile``."""

    html: str
    summary: dict
    battletag: str | None
    name: str | None
    last_updated_blizzard: int | None
    updated_at: int
    data_version: int


class StorageStats(TypedDict):
    """Storage statistics as returned by ``get_stats``."""

    size_bytes: int
    static_data_count: int
    player_profiles_count: int
    player_profile_age_p50: float
    player_profile_age_p90: float
    player_profile_age_p99: float


class StoragePort(Protocol):
    """Protocol for persistent storage operations.

    Defines the contract for storage adapters to implement persistent
    caching of static data and player profiles.
    """

    async def initialize(self) -> None:
        """Initialize storage (create tables, setup schema)"""
        ...

    async def get_static_data(self, key: str) -> StoredStaticData | None:
        """Get static data (heroes, maps, gamemodes, roles) by key.

        ``data`` is raw HTML or JSON; ``updated_at`` is a Unix timestamp.
        Returns None if not found.
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

    async def get_player_profile(self, player_id: str) -> StoredPlayerProfile | None:
        """
        Get player profile HTML and parsed summary.

        ``updated_at`` is a Unix timestamp. Returns None if not found.
        """
        ...

    async def get_player_id_by_battletag(self, battletag: str) -> str | None:
        """
        Get the canonical player ID for a given battletag.

        Enables lookup optimisation: when a battletag has been seen before,
        the stored player ID can be used directly without an extra resolution step.

        Returns:
            Player ID if found, None otherwise
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

    async def get_stats(self) -> StorageStats:
        """Get storage statistics for monitoring."""
        ...

    async def close(self) -> None:
        """Close storage connections"""
        ...
