# pylint: disable=C0114,C0116,W0621
import json
from unittest.mock import Mock, patch

import pytest

from overfastapi.commands.check_and_update_cache import get_soon_expired_cache_keys
from overfastapi.commands.check_and_update_cache import (
    main as check_and_update_cache_main,
)
from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import MapGamemode, PlayerGamemode
from overfastapi.config import EXPIRED_CACHE_REFRESH_LIMIT


@pytest.fixture(scope="function")
def cache_manager():
    return CacheManager()


def test_check_and_update_maps_cache_to_update(
    cache_manager: CacheManager, maps_html_data: list
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players?name=TeKrop", "[...]", EXPIRED_CACHE_REFRESH_LIMIT + 30
    )
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 5)
    cache_manager.update_api_cache("/maps", "[...]", EXPIRED_CACHE_REFRESH_LIMIT - 5)
    cache_manager.update_api_cache(
        "/maps/gamemodes", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 100
    )

    cache_manager.update_parser_cache(
        "/heroes",
        {
            "hash": "098f6bcd4621d373cade4e832627b4f6",
            "data": '[{"name":"Sojourn"}]',
        },
    )

    # Check data in db (assert no API Cache data for subroutes)
    for gamemode in MapGamemode:
        assert not cache_manager.get_api_cache(f"/maps?gamemode={gamemode.value}")
        assert not cache_manager.get_parser_cache(f"/maps?gamemode={gamemode.value}")

    assert get_soon_expired_cache_keys() == {"/maps"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=maps_html_data,
        ),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating all cache for {} key...", "/maps")
    for gamemode in MapGamemode:
        assert cache_manager.get_api_cache(f"/maps?gamemode={gamemode.value}")
        assert cache_manager.get_parser_cache(f"/maps?gamemode={gamemode.value}")


@pytest.mark.parametrize(
    "hero_html_data,hero_json_data",
    [("ana", "ana")],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_check_and_update_specific_hero_to_update(
    cache_manager: CacheManager, hero_html_data: str, hero_json_data: dict
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_api_cache("/heroes/ana")
    assert not cache_manager.get_parser_cache("/heroes/ana")
    assert get_soon_expired_cache_keys() == {"/heroes/ana"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=hero_html_data,
        ),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating all cache for {} key...", "/heroes/ana")

    dumped_hero_json_data = json.dumps(hero_json_data)
    assert (
        cache_manager.get_api_cache("/heroes/ana").decode("utf-8")
        == dumped_hero_json_data
    )
    assert (
        cache_manager.get_parser_cache("/heroes/ana")[b"data"].decode("utf-8")
        == dumped_hero_json_data
    )


@pytest.mark.parametrize(
    "player_id,player_level,player_html_data,player_json_data",
    [("TeKrop-2217", 2415, "TeKrop-2217", "TeKrop-2217")],
    indirect=["player_html_data", "player_json_data"],
)
def test_check_and_update_specific_player_to_update(
    cache_manager: CacheManager,
    player_id: str,
    player_level: int,
    player_html_data: str,
    player_json_data: dict,
):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players/pc/TeKrop-2217", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_api_cache(
        "/players/pc/TeKrop-2217/summary", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )
    cache_manager.update_api_cache(
        f"/players/pc/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}",
        "{}",
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )
    cache_manager.update_api_cache(
        f"/players/pc/TeKrop-2217/stats?gamemode={PlayerGamemode.COMPETITIVE}",
        "{}",
        EXPIRED_CACHE_REFRESH_LIMIT - 5,
    )
    cache_manager.update_api_cache(
        "/players/pc/TeKrop-2217/achievements", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_api_cache("/players/pc/TeKrop-2217")
    assert not cache_manager.get_parser_cache("/players/pc/TeKrop-2217")
    assert get_soon_expired_cache_keys() == {"/players/pc/TeKrop-2217"}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        side_effect=[
            Mock(
                status_code=200,
                text=player_html_data,
            ),
            Mock(
                status_code=200,
                json=lambda: [{"urlName": player_id, "level": player_level}],
            ),
        ],
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call(
        "Updating all cache for {} key...", "/players/pc/TeKrop-2217"
    )

    dumped_player_json_data = json.dumps(player_json_data)

    assert (
        cache_manager.get_api_cache("/players/pc/TeKrop-2217").decode("utf-8")
        == dumped_player_json_data
    )

    assert (
        cache_manager.get_parser_cache("/players/pc/TeKrop-2217")[b"data"].decode(
            "utf-8"
        )
        == dumped_player_json_data
    )

    assert cache_manager.get_api_cache("/players/pc/TeKrop-2217/summary").decode(
        "utf-8"
    ) == json.dumps(player_json_data["summary"])

    assert cache_manager.get_api_cache(
        f"/players/pc/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}"
    ).decode("utf-8") == json.dumps(player_json_data["quickplay"]["career_stats"])

    assert cache_manager.get_api_cache(
        f"/players/pc/TeKrop-2217/stats?gamemode={PlayerGamemode.COMPETITIVE}"
    ).decode("utf-8") == json.dumps(player_json_data["competitive"]["career_stats"])

    assert cache_manager.get_api_cache("/players/pc/TeKrop-2217/achievements").decode(
        "utf-8"
    ) == json.dumps(player_json_data["achievements"])


def test_check_and_update_cache_no_update(cache_manager: CacheManager):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache(
        "/players?name=TeKrop", "[...]", EXPIRED_CACHE_REFRESH_LIMIT + 30
    )
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 5)
    cache_manager.update_api_cache("/maps", "[...]", EXPIRED_CACHE_REFRESH_LIMIT + 10)
    cache_manager.update_api_cache(
        "/maps/gamemodes", "{}", EXPIRED_CACHE_REFRESH_LIMIT + 100
    )

    cache_manager.update_parser_cache(
        "/heroes",
        {
            "hash": "098f6bcd4621d373cade4e832627b4f6",
            "data": '[{"name":"Sojourn"}]',
        },
    )

    assert get_soon_expired_cache_keys() == set()

    # check and update (no update)
    logger_info_mock = Mock()
    with patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_and_update_cache_main()

    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 0)


def test_check_error_from_blizzard(cache_manager: CacheManager):
    # Add some data (to update and not to update)
    cache_manager.update_api_cache("/heroes/ana", "{}", EXPIRED_CACHE_REFRESH_LIMIT - 5)

    # check and update (only maps should be updated)
    logger_error_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=500,
            text="Internal Server Error",
        ),
    ), patch("overfastapi.common.logging.logger.error", logger_error_mock):
        check_and_update_cache_main()

    # Check data in db (assert we created API Cache for subroutes)
    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}", 500, "Internal Server Error"
    )
