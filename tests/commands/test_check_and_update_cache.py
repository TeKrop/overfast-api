import json
from unittest.mock import Mock, patch

import pytest

from overfastapi.commands.check_and_update_cache import get_soon_expired_cache_keys
from overfastapi.commands.check_and_update_cache import (
    main as check_and_update_cache_main,
)
from overfastapi.common.cache_manager import CacheManager
from overfastapi.config import BLIZZARD_HOST, EXPIRED_CACHE_REFRESH_LIMIT, HEROES_PATH


@pytest.fixture(scope="function")
def cache_manager():
    return CacheManager()


def test_check_and_update_gamemodes_cache_to_update(
    cache_manager: CacheManager, home_html_data: list, gamemodes_json_data: dict
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 5)
    cache_manager.update_api_cache(
        "/gamemodes", "[...]", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    assert get_soon_expired_cache_keys() == {"/gamemodes"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=home_html_data),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating all cache for {} key...", "/gamemodes")

    assert (
        json.loads(cache_manager.get_api_cache("/gamemodes").decode("utf-8"))
        == gamemodes_json_data
    )


@pytest.mark.parametrize(
    "hero_html_data,hero_json_data",
    [("ana", "ana")],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_check_and_update_specific_hero_to_update(
    cache_manager: CacheManager,
    hero_html_data: str,
    hero_json_data: dict,
    heroes_html_data: str,
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_api_cache("/heroes/ana")
    assert get_soon_expired_cache_keys() == {"/heroes/ana"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        side_effect=[
            Mock(status_code=200, text=hero_html_data),
            Mock(status_code=200, text=heroes_html_data),
        ],
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating all cache for {} key...", "/heroes/ana")

    assert (
        json.loads(cache_manager.get_api_cache("/heroes/ana").decode("utf-8"))
        == hero_json_data
    )


def test_check_and_update_cache_no_update(cache_manager: CacheManager):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 5)
    cache_manager.update_api_cache(
        "/gamemodes", "[...]", EXPIRED_CACHE_REFRESH_LIMIT + 10
    )

    assert get_soon_expired_cache_keys() == set()

    # check and update (no update)
    logger_info_mock = Mock()
    with patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 0)


@pytest.mark.parametrize(
    "hero_html_data,hero_json_data",
    [("ana", "ana")],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_check_and_update_from_parser(
    cache_manager: CacheManager,
    hero_html_data: str,
    hero_json_data: dict,
    heroes_html_data: str,
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    blizzard_ana_url = f"{BLIZZARD_HOST}{HEROES_PATH}/ana"
    blizzard_page_hash = "8b466193105afbdb774a210e042938fe"

    cache_manager.update_parser_cache(
        blizzard_ana_url,
        {
            "hash": blizzard_page_hash.encode("utf-8"),
            "data": json.dumps(hero_json_data),
        },
    )

    # Check data in db
    assert cache_manager.get_api_cache("/heroes/ana")
    assert cache_manager.get_parser_cache(blizzard_ana_url)
    assert cache_manager.get_unchanged_parser_cache(
        blizzard_ana_url, blizzard_page_hash
    )

    assert get_soon_expired_cache_keys() == {"/heroes/ana"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        side_effect=[
            Mock(status_code=200, text=hero_html_data),
            Mock(status_code=200, text=heroes_html_data),
        ],
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check that we found parser cache
    logger_info_mock.assert_any_call("Parser Cache found !")

    assert (
        json.loads(cache_manager.get_api_cache("/heroes/ana").decode("utf-8"))
        == hero_json_data
    )


def test_check_error_from_blizzard(cache_manager: CacheManager):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    # check and update (only maps should be updated)
    logger_error_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(status_code=500, text="Internal Server Error"),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}", 500, "Internal Server Error"
    )
