from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import fakeredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.adapters.blizzard import BlizzardClient
from app.api.dependencies import get_storage
from app.main import app
from tests.fake_storage import FakeStorage


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest_asyncio.fixture(scope="session")
async def valkey_server():
    """Provide async FakeValkey server for tests"""
    return fakeredis.FakeAsyncRedis(protocol=3)


@pytest_asyncio.fixture(scope="session")
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
    # Flush Valkey and clear all storage data before every test
    await valkey_server.flushdb()
    await storage_db.clear_all_data()

    # Reset in-memory rate limit state on the singleton
    BlizzardClient()._rate_limited_until = 0
    app.dependency_overrides[get_storage] = lambda: storage_db

    with (
        patch("app.helpers.settings.discord_webhook_enabled", False),
        patch("app.helpers.settings.profiler", None),
        patch(
            "app.adapters.cache.valkey_cache.ValkeyCache.valkey_server",
            valkey_server,
        ),
    ):
        yield

    app.dependency_overrides.pop(get_storage, None)

    await valkey_server.flushdb()
    await storage_db.clear_all_data()
