import json
from unittest.mock import Mock, patch

import pytest
import requests

from overfastapi.commands.check_and_update_cache import get_soon_expired_cache_keys
from overfastapi.commands.check_and_update_cache import (
    main as check_and_update_cache_main,
)
from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import HeroKeyCareerFilter, PlayerGamemode, PlayerPlatform
from overfastapi.config import (
    BLIZZARD_HOST,
    CAREER_PATH,
    EXPIRED_CACHE_REFRESH_LIMIT,
    HEROES_PATH,
)


@pytest.fixture(scope="function")
def cache_manager():
    return CacheManager()


def test_check_and_update_gamemodes_cache_to_update(
    cache_manager: CacheManager, home_html_data: list, gamemodes_json_data: dict
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players?name=TeKrop", "[...]", EXPIRED_CACHE_REFRESH_LIMIT + 30
    )
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
    cache_manager.update_api_cache(
        "/players?name=TeKrop", "[...]", EXPIRED_CACHE_REFRESH_LIMIT + 30
    )
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


@pytest.mark.parametrize(
    "player_id,player_html_data,player_json_data",
    [("TeKrop-2217", "TeKrop-2217", "TeKrop-2217")],
    indirect=["player_html_data", "player_json_data"],
)
def test_check_and_update_specific_player_to_update(
    cache_manager: CacheManager,
    player_id: str,
    player_html_data: str,
    player_json_data: dict,
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players/TeKrop-2217", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_api_cache(
        "/players/TeKrop-2217/summary", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_api_cache(
        f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}",
        "{}",
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )
    cache_manager.update_api_cache(
        f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.COMPETITIVE}",
        "{}",
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )

    blizzard_career_url = f"{BLIZZARD_HOST}{CAREER_PATH}/TeKrop-2217/"

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_api_cache("/players/TeKrop-2217")
    assert not cache_manager.get_parser_cache(blizzard_career_url)
    assert get_soon_expired_cache_keys() == {"/players/TeKrop-2217"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=player_html_data,
        ),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call(
        "Updating all cache for {} key...", "/players/TeKrop-2217"
    )

    dumped_player_json_data = json.dumps(player_json_data)

    assert (
        cache_manager.get_api_cache("/players/TeKrop-2217").decode("utf-8")
        == dumped_player_json_data
    )

    assert (
        cache_manager.get_parser_cache(blizzard_career_url)[b"data"].decode("utf-8")
        == dumped_player_json_data
    )

    assert cache_manager.get_api_cache("/players/TeKrop-2217/summary").decode(
        "utf-8"
    ) == json.dumps(player_json_data["summary"])

    assert cache_manager.get_api_cache(
        f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}",
    ).decode("utf-8") == json.dumps(
        player_json_data["stats"]["pc"]["quickplay"]["career_stats"]
    )

    assert cache_manager.get_api_cache(
        f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.COMPETITIVE}",
    ).decode("utf-8") == json.dumps(
        player_json_data["stats"]["pc"]["competitive"]["career_stats"]
    )

    assert cache_manager.get_api_cache(
        (
            "/players/TeKrop-2217/stats?"
            f"gamemode={PlayerGamemode.QUICKPLAY}"
            f"&platform={PlayerPlatform.PC}"
            f"&hero={HeroKeyCareerFilter.REINHARDT}"
        ),
    ).decode("utf-8") == json.dumps(
        {
            "reinhardt": player_json_data["stats"]["pc"]["quickplay"]["career_stats"][
                "reinhardt"
            ]
        }
    )

    assert (
        cache_manager.get_api_cache(
            (
                "/players/TeKrop-2217/stats?"
                f"gamemode={PlayerGamemode.QUICKPLAY}"
                f"&platform={PlayerPlatform.CONSOLE}"
            ),
        ).decode("utf-8")
        == "{}"
    )

    assert (
        cache_manager.get_api_cache(
            (
                "/players/TeKrop-2217/stats?"
                f"gamemode={PlayerGamemode.QUICKPLAY}"
                f"&platform={PlayerPlatform.CONSOLE}"
                f"&hero={HeroKeyCareerFilter.ANA}"
            ),
        ).decode("utf-8")
        == "{}"
    )


def test_check_internal_error_from_blizzard(cache_manager: CacheManager):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    logger_error_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(status_code=500, text="Internal Server Error"),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        check_and_update_cache_main()

    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}", 500, "Internal Server Error"
    )


def test_check_timeout_from_blizzard(cache_manager: CacheManager):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    logger_error_mock = Mock()
    with patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        check_and_update_cache_main()

    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}",
        0,
        "Blizzard took more than 10 seconds to respond, resulting in a timeout",
    )


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_check_parser_parsing_error(cache_manager: CacheManager, player_html_data: str):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players/TeKrop-2217", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    logger_critical_mock = Mock()

    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"', 'class="blabla"'
    )
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_attr_error),
    ), patch("overfastapi.common.logging.logger.critical", logger_critical_mock):
        check_and_update_cache_main()

    logger_critical_mock.assert_called_with(
        "Internal server error for URL {} : {}",
        "https://overwatch.blizzard.com/en-us/career/TeKrop-2217/",
        "AttributeError(\"'NoneType' object has no attribute 'find'\")",
    )


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_check_parser_init_error(cache_manager: CacheManager, player_html_data: str):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players/TeKrop-2217", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    logger_error_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        check_and_update_cache_main()

    logger_error_mock.assert_any_call(
        "Failed to instanciate Parser when refreshing : {}", "Player not found"
    )


def test_check_players_search_never_to_refresh(cache_manager: CacheManager):
    # The key will expire soon but shouldn't be in the list of keys to refresh
    cache_manager.update_api_cache(
        "/players?name=TeKrop", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    # Another one that should be
    cache_manager.update_api_cache("/heroes", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)
    assert get_soon_expired_cache_keys() == {"/heroes"}
