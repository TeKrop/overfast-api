"""Cache port protocol for dependency injection"""

from typing import Protocol


class CachePort(Protocol):
    """Protocol for cache operations"""

    async def get(self, key: str) -> bytes | None:
        """Get value from cache by key"""
        ...

    async def set(
        self,
        key: str,
        value: bytes,
        expire: int | None = None,
    ) -> None:
        """Set value in cache with optional expiration (seconds)"""
        ...

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        ...
