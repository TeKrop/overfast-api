from unittest.mock import patch

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def valkey_server():
    return fakeredis.FakeValkey(protocol=3)


@pytest.fixture(autouse=True)
def _patch_before_every_test(valkey_server: fakeredis.FakeValkey):
    # Flush Valkey before and after every tests
    valkey_server.flushdb()

    with (
        patch("app.helpers.settings.discord_webhook_enabled", False),
        patch("app.helpers.settings.profiler", None),
        patch(
            "app.cache_manager.CacheManager.valkey_server",
            valkey_server,
        ),
    ):
        yield

    valkey_server.flushdb()
