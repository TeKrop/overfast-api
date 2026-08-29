"""FastAPI application lifespan context manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.adapters.blizzard import BlizzardClient
from app.adapters.cache import ValkeyCache
from app.adapters.storage import PostgresStorage
from app.adapters.tasks.worker import broker
from app.infrastructure.logger import logger

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.domain.ports import BlizzardClientPort, CachePort


@asynccontextmanager
async def lifespan(_: FastAPI):  # pragma: no cover
    logger.info("Initializing PostgreSQL storage...")
    storage = PostgresStorage()
    await storage.initialize()

    logger.info("Instanciating HTTPX AsyncClient...")
    overfast_client: BlizzardClientPort = BlizzardClient()

    cache: CachePort = ValkeyCache()

    # The worker runs this same lifespan (see app/adapters/tasks/worker.py),
    # so everything touching the shared api-cache must be app-process only —
    # a worker restart would otherwise wipe the cache nginx serves from and
    # send every subsequent request to Blizzard behind the throttle.
    if not broker.is_worker_process:
        # Evict stale api-cache data on startup (handles crash/deploy scenarios)
        await cache.evict_volatile_data()

        logger.info("Starting Valkey task broker...")
        await broker.startup()

    yield

    # Properly close HTTPX Async Client and PostgreSQL storage
    await overfast_client.close()

    # Same reasoning as startup: a worker shutting down must not evict the
    # cache the app process is still serving from, nor trigger a BGSAVE.
    if not broker.is_worker_process:
        # Evict volatile Valkey data (api-cache, rate-limit, etc.) before RDB snapshot
        await cache.evict_volatile_data()
        # Evict low-signal unknown-player entries before persisting the RDB snapshot
        await cache.evict_low_count_player_statuses()
        await cache.bgsave()

    await storage.close()

    if not broker.is_worker_process:
        await broker.shutdown()
