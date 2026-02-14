from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import fakeredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.adapters.storage import SQLiteStorage
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest_asyncio.fixture(scope="session")
async def valkey_server():
    """Provide async FakeValkey server for tests"""
    return fakeredis.FakeAsyncRedis(protocol=3)


@pytest_asyncio.fixture(scope="session")
async def storage_db() -> AsyncIterator[SQLiteStorage]:
    """Provide an in-memory SQLite storage for tests"""

    storage = SQLiteStorage(db_path=":memory:")
    await storage.initialize()
    yield storage
    await storage.close()


@pytest_asyncio.fixture(autouse=True)
async def _patch_before_every_test(
    valkey_server: fakeredis.FakeAsyncRedis,  # Async FakeValkey
    storage_db: SQLiteStorage,
):
    # Flush Valkey and SQLite player data before and after every test
    await valkey_server.flushdb()
    await storage_db.clear_player_data()

    with (
        patch("app.helpers.settings.discord_webhook_enabled", False),
        patch("app.helpers.settings.profiler", None),
        patch(
            "app.cache_manager.CacheManager.valkey_server",
            valkey_server,
        ),
        patch(
            "app.controllers.AbstractController.storage",
            storage_db,
        ),
    ):
        yield

    await valkey_server.flushdb()
    await storage_db.clear_player_data()
