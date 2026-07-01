"""Blizzard client port protocol for dependency injection"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import httpx2


class BlizzardClientPort(Protocol):
    """Protocol for Blizzard API/web client operations"""

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx2.Response:
        """GET request to the given URL, respecting configured throttling."""
        ...

    async def close(self) -> None:
        """Close HTTP client connections"""
        ...
