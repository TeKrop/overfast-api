from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import fakeredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.adapters.blizzard.client import BlizzardClient
from app.adapters.blizzard.throttle import BlizzardThrottle
from app.adapters.cache.valkey_cache import ValkeyCache
from app.adapters.tasks.asyncio_task_queue import AsyncioTaskQueue
from app.api.dependencies import get_storage, get_task_queue
from app.main import app
from app.metaclasses import Singleton
from tests.fake_storage import FakeStorage


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def valkey_server() -> fakeredis.FakeAsyncRedis:
    """Fresh FakeAsyncRedis per test with no event-loop binding at creation time.

    Using a sync (non-async) fixture avoids binding asyncio.Lock to the
    pytest-asyncio function loop, which differs from TestClient's internal loop.
    """
    return fakeredis.FakeAsyncRedis(protocol=3)


@pytest_asyncio.fixture
async def storage_db() -> AsyncIterator[FakeStorage]:
    """Provide in-memory FakeStorage for tests"""
    storage = FakeStorage()
    await storage.initialize()
    yield storage
    await storage.close()


@pytest_asyncio.fixture(autouse=True)
async def _patch_before_every_test(
    valkey_server: fakeredis.FakeAsyncRedis,
    storage_db: FakeStorage,
):
    # Clear all storage data before every test
    await storage_db.clear_all_data()

    # Reset throttle singleton so penalty state doesn't bleed between tests
    Singleton._instances.pop(BlizzardThrottle, None)
    # Reset BlizzardClient singleton so it doesn't hold stale throttle/cache references
    Singleton._instances.pop(BlizzardClient, None)
    # Reset ValkeyCache singleton so each test gets a fresh redis client in the current event loop
    Singleton._instances.pop(ValkeyCache, None)
    # Reset asyncio task queue (used in tests instead of arq)
    Singleton._instances.pop(AsyncioTaskQueue, None)
    AsyncioTaskQueue._pending_jobs.clear()

    app.dependency_overrides[get_storage] = lambda: storage_db
    # Use in-process asyncio task queue in tests (avoids arq/redis event loop conflicts)
    app.dependency_overrides[get_task_queue] = lambda: AsyncioTaskQueue()

    with (
        patch("app.helpers.settings.discord_webhook_enabled", False),
        patch("app.helpers.settings.profiler", None),
        patch(
            "app.adapters.cache.valkey_cache.valkey.Valkey",
            return_value=valkey_server,
        ),
    ):
        yield

    app.dependency_overrides.pop(get_storage, None)
    app.dependency_overrides.pop(get_task_queue, None)

    await storage_db.clear_all_data()
