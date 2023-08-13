from unittest.mock import Mock, patch

import pytest

from app.commands.check_and_delete_parser_cache import get_soon_expired_cache_keys
from app.commands.check_and_delete_parser_cache import (
    main as check_and_delete_parser_cache_main,
)
from app.common.cache_manager import CacheManager
from app.common.enums import Locale
from app.config import settings


@pytest.fixture()
def cache_manager():
    return CacheManager()


@pytest.fixture()
def locale():
    return Locale.ENGLISH_US


def test_check_and_delete_parser_cache_some_to_delete(
    cache_manager: CacheManager,
    locale: str,
):
    # Add some data, with some which is expired and some which is not. Only the
    # parser cache last update needs to be expired for the process to work
    cache_key_prefix = (
        f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}"
    )

    # Parser Cache is up-to-date, but it hasn't been retrieved from API
    # call since a long time : we'll delete it
    first_cache_key = f"{cache_key_prefix}/Player-0001"
    cache_manager.update_parser_cache(
        first_cache_key,
        {},
        settings.expired_cache_refresh_limit + 10,
    )
    cache_manager.update_parser_cache_last_update(
        first_cache_key,
        settings.expired_cache_refresh_limit - 10,
    )

    # Parser Cache is up-to-date and has been recently retrieved from API call,
    # no need to delete it.
    second_cache_key = f"{cache_key_prefix}/Player-0002"
    cache_manager.update_parser_cache(
        second_cache_key,
        {},
        settings.expired_cache_refresh_limit + 10,
    )
    cache_manager.update_parser_cache_last_update(
        second_cache_key,
        settings.expired_cache_refresh_limit + 10,
    )

    # Parser Cache is outdated and has been recently retrieved from API call,
    # no need to delete it.
    third_cache_key = f"{cache_key_prefix}/Player-0003"
    cache_manager.update_parser_cache(
        third_cache_key,
        {},
        settings.expired_cache_refresh_limit - 10,
    )
    cache_manager.update_parser_cache_last_update(
        third_cache_key,
        settings.expired_cache_refresh_limit + 10,
    )

    # Parser Cache is outdated and it hasn't been retrieved from API
    # call since a long time : we'll delete it
    fourth_cache_key = f"{cache_key_prefix}/Player-0004"
    cache_manager.update_parser_cache(
        fourth_cache_key,
        {},
        settings.expired_cache_refresh_limit - 10,
    )
    cache_manager.update_parser_cache_last_update(
        fourth_cache_key,
        settings.expired_cache_refresh_limit - 10,
    )

    # Only the first and fourth keys should be deleted
    assert get_soon_expired_cache_keys() == {first_cache_key, fourth_cache_key}
    assert cache_manager.get_parser_cache(first_cache_key) == {}
    assert cache_manager.get_parser_cache(second_cache_key) == {}
    assert cache_manager.get_parser_cache(third_cache_key) == {}
    assert cache_manager.get_parser_cache(fourth_cache_key) == {}

    # check and delete, we should delete the first player
    logger_info_mock = Mock()
    with patch("app.common.logging.logger.info", logger_info_mock):
        check_and_delete_parser_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Deleting {} keys from Redis...", 2)

    assert get_soon_expired_cache_keys() == set()
    assert cache_manager.get_parser_cache(first_cache_key) is None
    assert cache_manager.get_parser_cache(second_cache_key) == {}
    assert cache_manager.get_parser_cache(third_cache_key) == {}
    assert cache_manager.get_parser_cache(fourth_cache_key) is None


def test_check_and_delete_parser_cache_no_cache_to_delete(
    cache_manager: CacheManager,
    locale: str,
):
    # Add some data which is not expiring
    cache_key = f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217"
    cache_manager.update_parser_cache(
        cache_key,
        {},
        settings.expired_cache_refresh_limit + 30,
    )
    cache_manager.update_parser_cache_last_update(
        cache_key,
        settings.expired_cache_refresh_limit + 30,
    )

    assert get_soon_expired_cache_keys() == set()

    # check and delete (no delete)
    logger_info_mock = Mock()
    with pytest.raises(SystemExit), patch(
        "app.common.logging.logger.info",
        logger_info_mock,
    ):
        check_and_delete_parser_cache_main()

    assert get_soon_expired_cache_keys() == set()
    logger_info_mock.assert_any_call("No Parser key to delete, closing")
