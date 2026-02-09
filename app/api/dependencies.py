"""FastAPI dependency injection for adapters and services"""

from typing import Annotated

from fastapi import Depends

from app.adapters.blizzard.client import BlizzardClient
from app.cache_manager import CacheManager


def get_blizzard_client() -> BlizzardClient:
    """Dependency for Blizzard HTTP client"""
    return BlizzardClient()


def get_cache_manager() -> CacheManager:
    """Dependency for cache manager (Valkey)"""
    return CacheManager()


# Type aliases for cleaner dependency injection
BlizzardClientDep = Annotated[BlizzardClient, Depends(get_blizzard_client)]
CacheManagerDep = Annotated[CacheManager, Depends(get_cache_manager)]
