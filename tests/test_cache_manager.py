from time import sleep
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from valkey.exceptions import ValkeyError

from app.cache_manager import CacheManager
from app.config import settings
from app.enums import Locale

if TYPE_CHECKING:
    from fastapi import Request


@pytest.fixture
def cache_manager():
    return CacheManager()


@pytest.fixture
def locale():
    return Locale.ENGLISH_US


@pytest.mark.parametrize(
    ("req", "expected"),
    [
        (Mock(url=Mock(path="/heroes"), query_params=None), "/heroes"),
        (
            Mock(url=Mock(path="/heroes"), query_params="role=damage"),
            "/heroes?role=damage",
        ),
        (
            Mock(url=Mock(path="/players"), query_params="name=TeKrop"),
            "/players?name=TeKrop",
        ),
    ],
)
def test_get_cache_key_from_request(
    cache_manager: CacheManager,
    req: Request,
    expected: str,
):
    assert cache_manager.get_cache_key_from_request(req) == expected


@pytest.mark.parametrize(
    ("cache_key", "value", "expire", "sleep_time", "expected"),
    [
        ("/heroes", [{"name": "Sojourn"}], 10, 0, [{"name": "Sojourn"}]),
        ("/heroes", [{"name": "Sojourn"}], 1, 1, None),
    ],
)
def test_update_and_get_api_cache(
    cache_manager: CacheManager,
    cache_key: str,
    value: list,
    expire: int,
    sleep_time: int | None,
    expected: str | None,
):
    # Assert the value is not here before update
    assert cache_manager.get_api_cache(cache_key) is None

    # Update the API Cache and sleep if needed
    cache_manager.update_api_cache(cache_key, value, expire)
    sleep(sleep_time + 1)

    # Assert the value matches
    assert cache_manager.get_api_cache(cache_key) == expected
    assert cache_manager.get_api_cache("another_cache_key") is None


def test_valkey_connection_error(cache_manager: CacheManager):
    valkey_connection_error = ValkeyError(
        "Error 111 connecting to 127.0.0.1:6379. Connection refused.",
    )
    heroes_cache_key = (
        f"HeroesParser-{settings.blizzard_host}/{locale}{settings.heroes_path}"
    )
    with patch(
        "app.cache_manager.valkey.Valkey.get",
        side_effect=valkey_connection_error,
    ):
        cache_manager.update_api_cache(
            heroes_cache_key,
            [{"name": "Sojourn"}],
            settings.heroes_path_cache_timeout,
        )
        assert cache_manager.get_api_cache(heroes_cache_key) is None
