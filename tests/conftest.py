from unittest.mock import patch

import fakeredis
import pytest
from _pytest.fixtures import SubRequest

from app.common.helpers import read_html_file, read_json_file


@pytest.fixture(scope="session")
def redis_server():
    return fakeredis.FakeStrictRedis()


@pytest.fixture(autouse=True)
def _patch_before_every_test(redis_server: fakeredis.FakeStrictRedis):
    # Flush Redis before and after every tests
    redis_server.flushdb()

    with patch("app.common.helpers.settings.discord_webhook_enabled", False), patch(
        "app.common.cache_manager.CacheManager.redis_server",
        redis_server,
    ):
        yield

    redis_server.flushdb()


@pytest.fixture(scope="session")
def heroes_html_data():
    return read_html_file("heroes.html")


@pytest.fixture(scope="session")
def hero_html_data(request: SubRequest):
    return read_html_file(f"heroes/{request.param}.html")


@pytest.fixture(scope="session")
def home_html_data():
    return read_html_file("home.html")


@pytest.fixture(scope="session")
def player_html_data(request: SubRequest):
    return read_html_file(f"players/{request.param}.html")


@pytest.fixture(scope="session")
def search_html_data():
    return read_html_file("search.html")


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


@pytest.fixture(scope="session")
def player_json_data(request: SubRequest):
    return read_json_file(f"players/{request.param}.json")


@pytest.fixture(scope="session")
def player_stats_json_data(request: SubRequest):
    return read_json_file(f"players/stats/{request.param}.json")


@pytest.fixture(scope="session")
def player_career_json_data(request: SubRequest):
    return read_json_file(f"players/career/{request.param}.json")


@pytest.fixture(scope="session")
def search_players_blizzard_json_data():
    return read_json_file("search_players/search_players_blizzard_result.json")


@pytest.fixture(scope="session")
def search_tekrop_blizzard_json_data():
    return read_json_file("search_players/search_tekrop_blizzard_result.json")


@pytest.fixture(scope="session")
def search_players_api_json_data():
    return read_json_file("search_players/search_players_api_result.json")


@pytest.fixture(scope="session")
def maps_json_data():
    return read_json_file("maps.json")


@pytest.fixture(scope="session")
def namecards_json_data():
    return read_json_file("namecards.json")
