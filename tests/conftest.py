from unittest.mock import patch

import fakeredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.adapters.storage import SQLiteStorage
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def valkey_server():
    return fakeredis.FakeValkey(protocol=3)  # ty: ignore[possibly-missing-attribute]


@pytest_asyncio.fixture(scope="session")
async def storage_db() -> SQLiteStorage:
    """Provide an in-memory SQLite storage for tests"""

    storage = SQLiteStorage(db_path=":memory:")
    await storage.initialize()
    return storage


@pytest.fixture(autouse=True)
def _patch_before_every_test(
    valkey_server: fakeredis.FakeValkey,  # ty: ignore[possibly-missing-attribute]
    storage_db: SQLiteStorage,
):
    # Flush Valkey before and after every tests
    valkey_server.flushdb()

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

    valkey_server.flushdb()
