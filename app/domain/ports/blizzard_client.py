"""Blizzard client port protocol for dependency injection"""

from typing import Any, Protocol


class BlizzardResponse(Protocol):
    """Subset of an HTTP response read by the domain"""

    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    @property
    def url(self) -> object: ...

    def json(self) -> Any: ...


class BlizzardClientPort(Protocol):
    """Protocol for Blizzard API/web client operations"""

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> BlizzardResponse:
        """GET request to the given URL, respecting configured throttling."""
        ...

    async def aclose(self) -> None:
        """Close HTTP client connections"""
        ...
