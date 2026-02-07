"""Blizzard client port protocol for dependency injection"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import httpx


class BlizzardClientPort(Protocol):
    """Protocol for Blizzard API/web client operations"""

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """GET request to Blizzard URL with rate limiting"""
        ...

    async def close(self) -> None:
        """Close HTTP client connections"""
        ...
