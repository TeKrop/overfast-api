# pylint: disable=C0114,C0116
import json
from unittest.mock import patch

import pytest
import redis
from _pytest.fixtures import SubRequest

from overfastapi.config import REDIS_HOST, REDIS_PORT, TEST_FIXTURES_ROOT_PATH


@pytest.fixture(scope="session")
def redis_server():
    # Connect to Redis server, and stop tests if no Redis Server is running
    server = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    try:
        server.ping()
    except redis.exceptions.RedisError as err:
        pytest.exit(f"Redis server error : {str(err)}", 0)

    return server


@pytest.fixture(scope="function", autouse=True)
def patch_before_every_test(redis_server: redis.Redis):  # pylint: disable=W0621
    # Flush Redis before and after every tests
    redis_server.flushdb()

    with patch("overfastapi.common.helpers.DISCORD_WEBHOOK_ENABLED", False):
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
def maps_html_data():
    return read_html_file("maps.html")


@pytest.fixture(scope="session")
def hero_html_data(request: SubRequest):
    return read_html_file(f"hero/{request.param}.html")


@pytest.fixture(scope="session")
def player_html_data(request: SubRequest):
    return read_html_file(f"player/{request.param}.html")


def read_json_file(filepath: str) -> dict | list:
    with open(
        f"{TEST_FIXTURES_ROOT_PATH}/json/{filepath}", "r", encoding="utf-8"
    ) as json_file:
        return json.load(json_file)


@pytest.fixture(scope="session")
def heroes_json_data():
    return read_json_file("heroes.json")


@pytest.fixture(scope="session")
def maps_json_data():
    return read_json_file("maps.json")


@pytest.fixture(scope="session")
def map_gamemodes_json_data():
    return read_json_file("map_gamemodes.json")


@pytest.fixture(scope="session")
def hero_json_data(request: SubRequest):
    return read_json_file(f"hero/{request.param}.json")


@pytest.fixture(scope="session")
def player_json_data(request: SubRequest):
    return read_json_file(f"player/{request.param}.json")


@pytest.fixture(scope="session")
def search_players_blizzard_json_data():
    return read_json_file("search_players/search_players_blizzard_result.json")


@pytest.fixture(scope="session")
def search_players_api_json_data():
    return read_json_file("search_players/search_players_api_result.json")
