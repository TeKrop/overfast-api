from time import sleep
from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from redis.exceptions import RedisError

from app.common.cache_manager import CacheManager
from app.common.enums import Locale
from app.config import settings


@pytest.fixture()
def cache_manager():
    return CacheManager()


@pytest.fixture()
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
            Mock(url=Mock(path="/players"), query_params="name=TeKrop&privacy=public"),
            "/players?name=TeKrop&privacy=public",
        ),
    ],
)
def test_get_cache_key_from_request(
    cache_manager: CacheManager, req: Request, expected: str
):
    assert cache_manager.get_cache_key_from_request(req) == expected


@pytest.mark.parametrize(
    ("is_redis_server_up", "cache_key", "value", "expire", "sleep_time", "expected"),
    [
        (True, "/heroes", [{"name": "Sojourn"}], 10, None, b'[{"name":"Sojourn"}]'),
        (True, "/heroes", [{"name": "Sojourn"}], 1, 1, None),
        (False, "/heroes", [{"name": "Sojourn"}], 10, None, None),
        (False, "/heroes", [{"name": "Sojourn"}], 1, 1, None),
    ],
)
def test_update_and_get_api_cache(
    cache_manager: CacheManager,
    is_redis_server_up: bool,
    cache_key: str,
    value: list,
    expire: int,
    sleep_time: int | None,
    expected: str | None,
):
    with patch(
        "app.common.cache_manager.CacheManager.is_redis_server_up",
        is_redis_server_up,
    ):
        # Assert the value is not here before update
        assert cache_manager.get_api_cache(cache_key) is None

        # Update the API Cache and sleep if needed
        cache_manager.update_api_cache(cache_key, value, expire)
        if sleep_time:
            sleep(sleep_time)

        # Assert the value matches
        assert cache_manager.get_api_cache(cache_key) == expected
        assert cache_manager.get_api_cache("another_cache_key") is None


@pytest.mark.parametrize(
    ("is_redis_server_up", "cache_key", "parser_data"),
    [
        (
            True,
            "/heroes",
            [{"name": "Sojourn"}],
        ),
        (
            False,
            "/heroes",
            [{"name": "Sojourn"}],
        ),
    ],
)
def test_update_and_get_parser_cache(
    cache_manager: CacheManager,
    is_redis_server_up: bool,
    cache_key: str,
    parser_data: str,
):
    with patch(
        "app.common.cache_manager.CacheManager.is_redis_server_up",
        is_redis_server_up,
    ):
        # Assert the value is not here before update
        assert cache_manager.get_parser_cache(cache_key) is None

        # Update the Parser Cache and sleep if needed
        cache_manager.update_parser_cache(cache_key, parser_data, 10)

        # Assert the value matches
        assert cache_manager.get_parser_cache(cache_key) == (
            parser_data if is_redis_server_up else None
        )


@pytest.mark.parametrize(
    ("is_redis_server_up", "expected"),
    [
        (
            True,
            {
                f"{settings.parser_cache_key_prefix}:GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}",
                f"{settings.parser_cache_key_prefix}:HeroesParser-{settings.blizzard_host}/{locale}{settings.heroes_path}",
            },
        ),
        (False, set()),
    ],
)
def test_get_soon_expired_cache_keys(
    cache_manager: CacheManager, is_redis_server_up: bool, expected: set[str]
):
    with patch(
        "app.common.cache_manager.CacheManager.is_redis_server_up",
        is_redis_server_up,
    ):
        cache_manager.update_parser_cache(
            f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
            {},
            settings.expired_cache_refresh_limit + 5,
        )
        cache_manager.update_parser_cache(
            f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}",
            [],
            settings.expired_cache_refresh_limit - 5,
        )
        cache_manager.update_parser_cache(
            f"HeroesParser-{settings.blizzard_host}/{locale}{settings.heroes_path}",
            [{"name": "Sojourn"}],
            settings.expired_cache_refresh_limit - 10,
        )

        assert (
            set(
                cache_manager.get_soon_expired_cache_keys(
                    settings.parser_cache_key_prefix
                )
            )
            == expected
        )


def test_redis_connection_error(cache_manager: CacheManager):
    redis_connection_error = RedisError(
        "Error 111 connecting to 127.0.0.1:6379. Connection refused."
    )
    heroes_cache_key = (
        f"HeroesParser-{settings.blizzard_host}/{locale}{settings.heroes_path}"
    )
    with patch(
        "app.common.cache_manager.redis.Redis.get",
        side_effect=redis_connection_error,
    ):
        cache_manager.update_parser_cache(
            heroes_cache_key,
            [{"name": "Sojourn"}],
            settings.expired_cache_refresh_limit - 1,
        )
        assert cache_manager.get_parser_cache(heroes_cache_key) is None

    with patch(
        "app.common.cache_manager.redis.Redis.keys",
        side_effect=redis_connection_error,
    ):
        assert (
            set(
                cache_manager.get_soon_expired_cache_keys(
                    settings.parser_cache_key_prefix
                )
            )
            == set()
        )

    with patch(
        "app.common.cache_manager.redis.Redis.ttl",
        side_effect=redis_connection_error,
    ):
        assert (
            set(
                cache_manager.get_soon_expired_cache_keys(
                    settings.parser_cache_key_prefix
                )
            )
            == set()
        )
