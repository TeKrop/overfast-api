import re
from collections.abc import Callable
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import ParserBlizzardError, ParserParsingError
from app.players.enums import PlayerGamemode, PlayerPlatform
from app.players.helpers import players_ids
from app.players.parsers.player_career_parser import PlayerCareerParser


@pytest.mark.parametrize(
    ("player_career_parser", "player_html_data", "player_json_data", "kwargs_filter"),
    [
        (player_id, player_id, player_id, kwargs_filter)
        for player_id in players_ids
        for kwargs_filter in ({}, {"summary": True}, {"stats": True})
        if player_id != "Unknown-1234"
    ],
    indirect=["player_career_parser", "player_html_data", "player_json_data"],
)
@pytest.mark.asyncio
async def test_player_page_parsing_with_filters(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    player_json_data: dict,
    kwargs_filter: dict,
    player_search_response_mock: Mock,
    search_data_func: Callable[[str, str], str | None],
):
    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_html_data),
            ],
        ),
        patch(
            "app.cache_manager.CacheManager.get_search_data_cache",
            side_effect=search_data_func,
        ),
    ):
        await player_career_parser.parse()

    # Just check that the parsing is working properly
    player_career_parser.filter_request_using_query(**kwargs_filter)

    assert player_career_parser.data == player_json_data


@pytest.mark.parametrize(
    ("player_career_parser", "player_html_data", "gamemode", "platform"),
    [
        ("TeKrop-2217", "TeKrop-2217", gamemode, platform)
        for gamemode in (None, *PlayerGamemode)
        for platform in (None, *PlayerPlatform)
    ],
    indirect=["player_career_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_filter_all_stats_data(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    gamemode: PlayerGamemode | None,
    platform: PlayerPlatform | None,
    player_search_response_mock: Mock,
    search_data_func: Callable[[str, str], str | None],
):
    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_html_data),
            ],
        ),
        patch(
            "app.cache_manager.CacheManager.get_search_data_cache",
            side_effect=search_data_func,
        ),
    ):
        await player_career_parser.parse()

    # Just check that the parsing is working properly
    filtered_data = player_career_parser._filter_all_stats_data(
        platform=platform, gamemode=gamemode
    )

    if platform:
        assert all(
            platform_data is None
            for platform_key, platform_data in filtered_data.items()
            if filtered_data is not None and platform_key != platform
        )

    if gamemode:
        assert all(
            gamemode_data is None
            for platform_key, platform_data in filtered_data.items()
            if platform_data is not None
            for gamemode_key, gamemode_data in platform_data.items()
            if gamemode_key != gamemode
        )

    if not platform and not gamemode:
        assert filtered_data == player_career_parser.data["stats"]


@pytest.mark.parametrize(
    ("player_career_parser"),
    [("Unknown-1234")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_unknown_player_career_parser_blizzard_error(
    player_career_parser: PlayerCareerParser,
    player_search_response_mock: Mock,
):
    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=player_search_response_mock,
        ),
    ):
        await player_career_parser.parse()


@pytest.mark.parametrize(
    ("player_career_parser", "player_html_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_career_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_career_parser_parsing_error_attribute_error(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    player_search_response_mock: Mock,
):
    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"',
        'class="blabla"',
    )

    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_attr_error),
            ],
        ),
        pytest.raises(ParserParsingError) as error,
    ):
        await player_career_parser.parse()

    assert (
        error.value.message
        == "AttributeError(\"'NoneType' object has no attribute 'find'\")"
    )


@pytest.mark.parametrize(
    ("player_career_parser", "player_html_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_career_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_career_parser_parsing_error_key_error(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    player_search_response_mock: Mock,
):
    player_key_error = re.sub(
        'class="Profile-playerSummary--endorsement" src="[^"]*"',
        'class="Profile-playerSummary--endorsement"',
        player_html_data,
    )

    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_key_error),
            ],
        ),
        pytest.raises(ParserParsingError) as error,
    ):
        await player_career_parser.parse()

    assert error.value.message == "KeyError('src')"


@pytest.mark.parametrize(
    ("player_career_parser", "player_html_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_career_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_career_parser_parsing_error_type_error(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    player_search_response_mock: Mock,
):
    player_type_error = player_html_data.replace(
        'class="Profile-playerSummary--endorsement"',
        "",
    )

    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_type_error),
            ],
        ),
        pytest.raises(ParserParsingError) as error,
    ):
        await player_career_parser.parse()

    assert (
        error.value.message == "TypeError(\"'NoneType' object is not subscriptable\")"
    )
