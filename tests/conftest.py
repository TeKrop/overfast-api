from unittest.mock import patch

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def redis_server():
    return fakeredis.FakeStrictRedis()


@pytest.fixture(autouse=True)
def _patch_before_every_test(redis_server: fakeredis.FakeStrictRedis):
    # Flush Redis before and after every tests
    redis_server.flushdb()

    with (
        patch("app.helpers.settings.discord_webhook_enabled", False),
        patch("app.helpers.settings.profiler", None),
        patch(
            "app.cache_manager.CacheManager.redis_server",
            redis_server,
        ),
    ):
        yield

    redis_server.flushdb()
