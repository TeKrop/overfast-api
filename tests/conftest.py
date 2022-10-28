# pylint: disable=C0114,C0116
import json
from unittest.mock import patch

import fakeredis
import pytest
from _pytest.fixtures import SubRequest

from overfastapi.config import TEST_FIXTURES_ROOT_PATH


@pytest.fixture(scope="session")
def redis_server():
    return fakeredis.FakeStrictRedis()


@pytest.fixture(scope="function", autouse=True)
def patch_before_every_test(
    redis_server: fakeredis.FakeStrictRedis,
):  # pylint: disable=W0621
    # Flush Redis before and after every tests
    redis_server.flushdb()

    with patch("overfastapi.common.helpers.DISCORD_WEBHOOK_ENABLED", False), patch(
        "overfastapi.common.cache_manager.CacheManager.redis_server", redis_server
    ):
        yield

    redis_server.flushdb()


def read_html_file(filepath: str) -> str:
    with open(
        f"{TEST_FIXTURES_ROOT_PATH}/html/{filepath}", "r", encoding="utf-8"
    ) as html_file:
        return html_file.read()


@pytest.fixture(scope="session")
def heroes_html_data():
    return read_html_file("heroes.html")


@pytest.fixture(scope="session")
def hero_html_data(request: SubRequest):
    return read_html_file(f"heroes/{request.param}.html")


@pytest.fixture(scope="session")
def home_html_data():
    return read_html_file("home.html")


def read_json_file(filepath: str) -> dict | list:
    with open(
        f"{TEST_FIXTURES_ROOT_PATH}/json/{filepath}", "r", encoding="utf-8"
    ) as json_file:
        return json.load(json_file)


@pytest.fixture(scope="session")
def heroes_json_data():
    return read_json_file("heroes.json")


@pytest.fixture(scope="session")
def hero_json_data(request: SubRequest):
    return read_json_file(f"heroes/{request.param}.json")


@pytest.fixture(scope="session")
def gamemodes_json_data():
    return read_json_file("gamemodes.json")


@pytest.fixture(scope="session")
def roles_json_data():
    return read_json_file("roles.json")
