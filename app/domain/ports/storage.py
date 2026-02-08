"""Storage port protocol for persistent data storage"""

from typing import Protocol


class StoragePort(Protocol):
    """Protocol for persistent storage operations (SQLite in v4)"""

    async def get_static_data(self, key: str) -> dict | None:
        """Get static data (heroes, maps, gamemodes, roles) by key"""
        ...

    async def set_static_data(self, key: str, data: dict, data_type: str) -> None:
        """Store static data with metadata"""
        ...

    async def get_player_profile(self, player_id: str) -> dict | None:
        """Get player profile HTML and parsed summary"""
        ...

    async def set_player_profile(
        self, player_id: str, html: str, summary: dict
    ) -> None:
        """Store player profile HTML and parsed summary"""
        ...

    async def close(self) -> None:
        """Close storage connections"""
        ...
