import asyncio
from unittest.mock import Mock, patch

import pytest
from httpx import TimeoutException

from overfastapi.commands.check_and_update_cache import get_soon_expired_cache_keys
from overfastapi.commands.check_and_update_cache import (
    main as check_and_update_cache_main,
)
from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import Locale
from overfastapi.common.helpers import overfast_client
from overfastapi.config import (
    BLIZZARD_HOST,
    CAREER_PATH,
    EXPIRED_CACHE_REFRESH_LIMIT,
    HEROES_PATH,
    HOME_PATH,
    PARSER_CACHE_KEY_PREFIX,
)


@pytest.fixture(scope="function")
def cache_manager():
    return CacheManager()


@pytest.fixture(scope="function")
def locale():
    return Locale.ENGLISH_US


def test_check_and_update_gamemodes_cache_to_update(
    cache_manager: CacheManager,
    locale: str,
    home_html_data: list,
    gamemodes_json_data: dict,
):
    gamemodes_cache_key = f"GamemodesParser-{BLIZZARD_HOST}/{locale}{HOME_PATH}"
    complete_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{gamemodes_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{BLIZZARD_HOST}/{locale}{CAREER_PATH}/TeKrop-2217",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT + 30,
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT + 5,
    )
    cache_manager.update_parser_cache(
        gamemodes_cache_key, [], EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only gamemodes should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=home_html_data),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert cache_manager.get_parser_cache(gamemodes_cache_key) == gamemodes_json_data


@pytest.mark.parametrize(
    "hero_html_data,hero_json_data",
    [("ana", "ana")],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_check_and_update_specific_hero_to_update(
    cache_manager: CacheManager, locale: str, hero_html_data: str, hero_json_data: dict
):
    ana_cache_key = f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana"
    complete_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{ana_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        ana_cache_key, {}, EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(ana_cache_key) == {}
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=hero_html_data),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    # Remove portrait as this is retrieved from heroes list
    hero_data = hero_json_data.copy()
    del hero_data["portrait"]

    assert cache_manager.get_parser_cache(ana_cache_key) == hero_data


def test_check_and_update_maps_to_update(
    cache_manager: CacheManager, maps_json_data: dict
):
    cache_key = "MapsParser"
    complete_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(cache_key, [], EXPIRED_CACHE_REFRESH_LIMIT - 5)

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(cache_key) == []
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()

    with patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert cache_manager.get_parser_cache(cache_key) == maps_json_data


def test_check_and_update_cache_no_update(cache_manager: CacheManager, locale: str):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{BLIZZARD_HOST}/{locale}{CAREER_PATH}/TeKrop-2217",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT + 30,
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT + 5,
    )
    cache_manager.update_parser_cache(
        f"GamemodesParser-{BLIZZARD_HOST}/{locale}{HOME_PATH}",
        [],
        EXPIRED_CACHE_REFRESH_LIMIT + 10,
    )

    assert get_soon_expired_cache_keys() == set()

    # check and update (no update)
    logger_info_mock = Mock()
    with patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 0)


@pytest.mark.parametrize(
    "player_id,player_html_data,player_json_data",
    [("TeKrop-2217", "TeKrop-2217", "TeKrop-2217")],
    indirect=["player_html_data", "player_json_data"],
)
def test_check_and_update_specific_player_to_update(
    cache_manager: CacheManager,
    locale: str,
    player_id: str,
    player_html_data: str,
    player_json_data: dict,
):
    player_cache_key = (
        f"PlayerParser-{BLIZZARD_HOST}/{locale}{CAREER_PATH}/TeKrop-2217/"
    )
    complete_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{player_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        player_cache_key, {}, EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT + 5,
    )
    cache_manager.update_parser_cache(
        f"GamemodesParser-{BLIZZARD_HOST}/{locale}{HOME_PATH}",
        [],
        EXPIRED_CACHE_REFRESH_LIMIT + 10,
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(player_cache_key) == {}
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=200,
            text=player_html_data,
        ),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert cache_manager.get_parser_cache(player_cache_key) == player_json_data


@pytest.mark.parametrize(
    "player_id,player_html_data,player_stats_json_data",
    [("TeKrop-2217", "TeKrop-2217", "TeKrop-2217")],
    indirect=["player_html_data", "player_stats_json_data"],
)
def test_check_and_update_player_stats_summary_to_update(
    cache_manager: CacheManager,
    locale: str,
    player_id: str,
    player_html_data: str,
    player_stats_json_data: dict,
):
    player_stats_cache_key = (
        f"PlayerStatsSummaryParser-{BLIZZARD_HOST}/{locale}{CAREER_PATH}/TeKrop-2217/"
    )
    complete_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{player_stats_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        player_stats_cache_key, {}, EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT + 5,
    )
    cache_manager.update_parser_cache(
        f"GamemodesParser-{BLIZZARD_HOST}/{locale}{HOME_PATH}",
        [],
        EXPIRED_CACHE_REFRESH_LIMIT + 10,
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(player_stats_cache_key) == {}
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=200,
            text=player_html_data,
        ),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert (
        cache_manager.get_parser_cache(player_stats_cache_key) == player_stats_json_data
    )


def test_check_internal_error_from_blizzard(cache_manager: CacheManager, locale: str):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )

    logger_error_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=500, text="Internal Server Error"),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        asyncio.run(check_and_update_cache_main())

    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}", 500, "Internal Server Error"
    )


def test_check_timeout_from_blizzard(cache_manager: CacheManager, locale: str):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"HeroParser-{BLIZZARD_HOST}/{locale}{HEROES_PATH}/ana",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )

    logger_error_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        asyncio.run(check_and_update_cache_main())

    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}",
        0,
        "Blizzard took more than 10 seconds to respond, resulting in a timeout",
    )


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_check_parser_parsing_error(
    cache_manager: CacheManager, locale: str, player_html_data: str
):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{BLIZZARD_HOST}/{locale}{CAREER_PATH}/TeKrop-2217",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )

    logger_critical_mock = Mock()

    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"', 'class="blabla"'
    )
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_attr_error),
    ), patch("overfastapi.common.logging.logger.critical", logger_critical_mock):
        asyncio.run(check_and_update_cache_main())

    logger_critical_mock.assert_called_with(
        "Internal server error for URL {} : {}",
        "https://overwatch.blizzard.com/en-us/career/TeKrop-2217/",
        "AttributeError(\"'NoneType' object has no attribute 'find'\")",
    )


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_check_parser_init_error(
    cache_manager: CacheManager, locale: str, player_html_data: str
):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{BLIZZARD_HOST}/{locale}{CAREER_PATH}/TeKrop-2217",
        {},
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )

    logger_error_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_html_data),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        asyncio.run(check_and_update_cache_main())

    logger_error_mock.assert_any_call(
        "Failed to instanciate Parser when refreshing : {}", "Player not found"
    )


def test_check_and_update_several_to_update(
    cache_manager: CacheManager,
    locale: str,
    home_html_data: list,
    gamemodes_json_data: dict,
    maps_json_data: dict,
):
    gamemodes_cache_key = f"GamemodesParser-{BLIZZARD_HOST}/{locale}{HOME_PATH}"
    maps_cache_key = "MapsParser"

    complete_gamemodes_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{gamemodes_cache_key}"
    complete_map_cache_key = f"{PARSER_CACHE_KEY_PREFIX}:{maps_cache_key}"

    # Add some data to update
    cache_manager.update_parser_cache(
        gamemodes_cache_key, [], EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_parser_cache(
        maps_cache_key, [], EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    assert get_soon_expired_cache_keys() == {
        complete_gamemodes_cache_key,
        complete_map_cache_key,
    }

    # check and update (only gamemodes should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=home_html_data),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 2)
    logger_info_mock.assert_any_call(
        "Updating data for {} key...", complete_gamemodes_cache_key
    )
    logger_info_mock.assert_any_call(
        "Updating data for {} key...", complete_map_cache_key
    )

    assert cache_manager.get_parser_cache(gamemodes_cache_key) == gamemodes_json_data
    assert cache_manager.get_parser_cache(maps_cache_key) == maps_json_data
