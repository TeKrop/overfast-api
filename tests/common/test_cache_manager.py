# pylint: disable=C0114,C0116,R0913,W0621
from time import sleep
from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from redis.exceptions import RedisError

from overfastapi.common.cache_manager import CacheManager
from overfastapi.config import API_CACHE_KEY_PREFIX, EXPIRED_CACHE_REFRESH_LIMIT


@pytest.fixture(scope="function")
def cache_manager():
    return CacheManager()


@pytest.mark.parametrize(
    "req,expected",
    [
        (Mock(url=Mock(path="/heroes"), query_params=None), "/heroes"),
        (
            Mock(url=Mock(path="/heroes"), query_params="role=damage"),
            "/heroes?role=damage",
        ),
    ],
)
def test_get_cache_key_from_request(
    cache_manager: CacheManager, req: Request, expected: str
):
    assert cache_manager.get_cache_key_from_request(req) == expected


@pytest.mark.parametrize(
    "is_redis_server_up,cache_key,value,expire,sleep_time,expected",
    [
        (True, "/heroes", '[{"name":"Sojourn"}]', 10, None, b'[{"name":"Sojourn"}]'),
        (True, "/heroes", '[{"name":"Sojourn"}]', 1, 1, None),
        (False, "/heroes", '[{"name":"Sojourn"}]', 10, None, None),
        (False, "/heroes", '[{"name":"Sojourn"}]', 1, 1, None),
    ],
)
def test_update_and_get_api_cache(
    cache_manager: CacheManager,
    is_redis_server_up: bool,
    cache_key: str,
    value: str,
    expire: int,
    sleep_time: int | None,
    expected: str | None,
):
    with patch(
        "overfastapi.common.cache_manager.CacheManager.is_redis_server_up",
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
    "is_redis_server_up,cache_key,parser_hash,parser_data",
    [
        (
            True,
            "/heroes",
            "098f6bcd4621d373cade4e832627b4f6",
            '[{"name":"Sojourn"}]',
        ),
        (
            False,
            "/heroes",
            "098f6bcd4621d373cade4e832627b4f6",
            '[{"name":"Sojourn"}]',
        ),
    ],
)
def test_update_and_get_parser_cache(
    cache_manager: CacheManager,
    is_redis_server_up: bool,
    cache_key: str,
    parser_hash: str,
    parser_data: str,
):
    with patch(
        "overfastapi.common.cache_manager.CacheManager.is_redis_server_up",
        is_redis_server_up,
    ):
        # Assert the value is not here before update
        assert cache_manager.get_parser_cache(cache_key) == (
            {} if is_redis_server_up else None
        )

        # Update the API Cache and sleep if needed
        cache_manager.update_parser_cache(
            cache_key,
            {"hash": parser_hash, "data": parser_data},
        )

        # Assert the value matches
        assert cache_manager.get_parser_cache(cache_key) == (
            {
                b"hash": parser_hash.encode("utf-8"),
                b"data": parser_data.encode("utf-8"),
            }
            if is_redis_server_up
            else None
        )

        # Assert it works with the valid parser_hash
        assert cache_manager.get_unchanged_parser_cache(cache_key, parser_hash) == (
            parser_data if is_redis_server_up else None
        )

        # Assert it doesn't works with an invalid parser_hash
        assert (
            cache_manager.get_unchanged_parser_cache(cache_key, "invalid_hash") is None
        )


@pytest.mark.parametrize(
    "is_redis_server_up,expected",
    [
        (
            True,
            {
                f"{API_CACHE_KEY_PREFIX}:/gamemodes",
            },
        ),
        (False, set()),
    ],
)
def test_get_soon_expired_api_cache_keys(
    cache_manager: CacheManager, is_redis_server_up: bool, expected: set[str]
):
    with patch(
        "overfastapi.common.cache_manager.CacheManager.is_redis_server_up",
        is_redis_server_up,
    ):
        cache_manager.update_api_cache(
            "/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 5
        )
        cache_manager.update_api_cache(
            "/gamemodes", "[...]", EXPIRED_CACHE_REFRESH_LIMIT - 5
        )
        cache_manager.update_parser_cache(
            "/heroes",
            {
                "hash": "098f6bcd4621d373cade4e832627b4f6",
                "data": '[{"name":"Sojourn"}]',
            },
        )

        assert set(cache_manager.get_soon_expired_api_cache_keys()) == expected


def test_redis_connection_error(cache_manager: CacheManager):
    redis_connection_error = RedisError(
        "Error 111 connecting to 127.0.0.1:6379. Connection refused."
    )
    with patch(
        "overfastapi.common.cache_manager.redis.Redis.get",
        side_effect=redis_connection_error,
    ):
        cache_manager.update_api_cache(
            "/heroes", '[{"name":"Sojourn"}]', EXPIRED_CACHE_REFRESH_LIMIT - 1
        )
        assert cache_manager.get_api_cache("/heroes") is None

    with patch(
        "overfastapi.common.cache_manager.redis.Redis.keys",
        side_effect=redis_connection_error,
    ):
        assert set(cache_manager.get_soon_expired_api_cache_keys()) == set()

    with patch(
        "overfastapi.common.cache_manager.redis.Redis.ttl",
        side_effect=redis_connection_error,
    ):
        assert set(cache_manager.get_soon_expired_api_cache_keys()) == set()
