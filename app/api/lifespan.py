"""FastAPI application lifespan context manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.adapters.blizzard import BlizzardClient
from app.adapters.cache import CacheManager
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

    # Evict stale api-cache data on startup (handles crash/deploy scenarios)
    cache: CachePort = CacheManager()
    await cache.evict_volatile_data()

    # Start broker for task dispatch (skipped in worker mode — taskiq handles it).
    if not broker.is_worker_process:
        logger.info("Starting Valkey task broker...")
        await broker.startup()

    yield

    # Properly close HTTPX Async Client and PostgreSQL storage
    await overfast_client.aclose()

    # Evict volatile Valkey data (api-cache, rate-limit, etc.) before RDB snapshot
    await cache.evict_volatile_data()
    await cache.bgsave()

    await storage.close()

    if not broker.is_worker_process:
        await broker.shutdown()
