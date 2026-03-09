"""FastAPI dependency injection for adapters and services"""

from typing import Annotated

from fastapi import Depends

from app.adapters.blizzard.client import BlizzardClient
from app.adapters.cache.valkey_cache import ValkeyCache
from app.adapters.storage.postgres_storage import PostgresStorage
from app.adapters.tasks.valkey_task_queue import ValkeyTaskQueue
from app.domain.ports import BlizzardClientPort, CachePort, StoragePort, TaskQueuePort
from app.domain.services import (
    GamemodeService,
    HeroService,
    MapService,
    PlayerService,
    RoleService,
)

# ---------------------------------------------------------------------------
# Low-level adapter dependencies
# ---------------------------------------------------------------------------


def get_blizzard_client() -> BlizzardClientPort:
    """Dependency for Blizzard HTTP client (Singleton)."""
    return BlizzardClient()


def get_cache() -> CachePort:
    """Dependency for Valkey cache (Singleton)."""
    return ValkeyCache()


def get_storage() -> StoragePort:
    """Dependency for PostgreSQL persistent storage (Singleton)."""
    return PostgresStorage()


def get_task_queue() -> TaskQueuePort:
    """Dependency for Valkey background task queue."""
    return ValkeyTaskQueue(ValkeyCache().valkey_server)


# ---------------------------------------------------------------------------
# Service dependencies
# ---------------------------------------------------------------------------


def get_hero_service(
    cache: CachePort = Depends(get_cache),
    storage: StoragePort = Depends(get_storage),
    blizzard_client: BlizzardClientPort = Depends(get_blizzard_client),
    task_queue: TaskQueuePort = Depends(get_task_queue),
) -> HeroService:
    return HeroService(cache, storage, blizzard_client, task_queue)


def get_map_service(
    cache: CachePort = Depends(get_cache),
    storage: StoragePort = Depends(get_storage),
    blizzard_client: BlizzardClientPort = Depends(get_blizzard_client),
    task_queue: TaskQueuePort = Depends(get_task_queue),
) -> MapService:
    return MapService(cache, storage, blizzard_client, task_queue)


def get_gamemode_service(
    cache: CachePort = Depends(get_cache),
    storage: StoragePort = Depends(get_storage),
    blizzard_client: BlizzardClientPort = Depends(get_blizzard_client),
    task_queue: TaskQueuePort = Depends(get_task_queue),
) -> GamemodeService:
    return GamemodeService(cache, storage, blizzard_client, task_queue)


def get_role_service(
    cache: CachePort = Depends(get_cache),
    storage: StoragePort = Depends(get_storage),
    blizzard_client: BlizzardClientPort = Depends(get_blizzard_client),
    task_queue: TaskQueuePort = Depends(get_task_queue),
) -> RoleService:
    return RoleService(cache, storage, blizzard_client, task_queue)


def get_player_service(
    cache: CachePort = Depends(get_cache),
    storage: StoragePort = Depends(get_storage),
    blizzard_client: BlizzardClientPort = Depends(get_blizzard_client),
    task_queue: TaskQueuePort = Depends(get_task_queue),
) -> PlayerService:
    return PlayerService(cache, storage, blizzard_client, task_queue)


# ---------------------------------------------------------------------------
# Type aliases for cleaner router injection
# ---------------------------------------------------------------------------

HeroServiceDep = Annotated[HeroService, Depends(get_hero_service)]
MapServiceDep = Annotated[MapService, Depends(get_map_service)]
GamemodeServiceDep = Annotated[GamemodeService, Depends(get_gamemode_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]
