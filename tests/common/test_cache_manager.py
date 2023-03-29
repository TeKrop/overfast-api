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


@pytest.fixture(autouse=True)
def _set_no_spread_percentage():
    with patch(
        "app.common.cache_manager.settings.parser_cache_expiration_spreading_percentage",
        0,
    ):
        yield


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
    timeout_value = 10

    with patch(
        "app.common.cache_manager.CacheManager.is_redis_server_up",
        is_redis_server_up,
    ), patch(
        "app.common.cache_manager.settings.parser_cache_expiration_spreading_percentage",
        25,
    ), patch(
        "app.common.helpers.randint",
        Mock(side_effect=lambda min_value, max_value: min_value),
    ) as randint_mock:
        # Assert the value is not here before update
        assert cache_manager.get_parser_cache(cache_key) is None

        # Update the Parser Cache and sleep if needed
        cache_manager.update_parser_cache(cache_key, parser_data, timeout_value)

        # Assert the value matches
        assert cache_manager.get_parser_cache(cache_key) == (
            parser_data if is_redis_server_up else None
        )

        # Assert the randint method has been called with the right parameters,
        # or hasn't been called at all, depending if redis server is up
        if is_redis_server_up:
            randint_mock.assert_called_once_with(
                int((75 / 100) * timeout_value),  # 100 - 25%
                int((125 / 100) * timeout_value),  # 100 + 25%
            )
        else:
            randint_mock.assert_not_called()


@pytest.mark.parametrize(
    ("is_redis_server_up", "expected"),
    [
        (
            True,
            {
                f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}",
                f"HeroesParser-{settings.blizzard_host}/{locale}{settings.heroes_path}",
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


def test_delete_keys(cache_manager: CacheManager):
    # Set data in parser cache which which is actually expired
    cache_manager.update_parser_cache(
        "/heroes", [{"name": "Sojourn"}], settings.expired_cache_refresh_limit - 1
    )
    cache_manager.update_parser_cache_last_update(
        "/heroes", settings.expired_cache_refresh_limit - 1
    )

    cache_manager.update_parser_cache(
        "/maps", [{"name": "Hanamura"}], settings.expired_cache_refresh_limit - 1
    )
    cache_manager.update_parser_cache_last_update(
        "/maps", settings.expired_cache_refresh_limit - 1
    )

    assert set(
        cache_manager.get_soon_expired_cache_keys(settings.parser_cache_key_prefix)
    ) == {"/heroes", "/maps"}
    assert set(
        cache_manager.get_soon_expired_cache_keys(
            settings.parser_cache_last_update_key_prefix
        )
    ) == {"/heroes", "/maps"}

    # Now delete the heroes key
    cache_manager.delete_keys(
        f"{prefix}:/heroes"
        for prefix in (
            settings.parser_cache_key_prefix,
            settings.parser_cache_last_update_key_prefix,
        )
    )

    # Check if the keys are not here anymore
    assert set(
        cache_manager.get_soon_expired_cache_keys(settings.parser_cache_key_prefix)
    ) == {"/maps"}
    assert set(
        cache_manager.get_soon_expired_cache_keys(
            settings.parser_cache_last_update_key_prefix
        )
    ) == {"/maps"}
