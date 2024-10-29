import re
from collections.abc import Callable
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import ParserBlizzardError, ParserParsingError
from app.players.helpers import players_ids
from app.players.parsers.player_parser import PlayerParser


@pytest.mark.parametrize(
    ("player_parser", "player_html_data", "player_json_data", "kwargs_filter"),
    [
        (player_id, player_id, player_id, kwargs_filter)
        for player_id in players_ids
        for kwargs_filter in ({}, {"summary": True}, {"stats": True})
        if player_id != "Unknown-1234"
    ],
    indirect=["player_parser", "player_html_data", "player_json_data"],
)
@pytest.mark.asyncio
async def test_player_page_parsing_with_filters(
    player_parser: PlayerParser,
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
        await player_parser.parse()

    # Just check that the parsing is working properly
    player_parser.filter_request_using_query(**kwargs_filter)

    assert player_parser.data == player_json_data


@pytest.mark.parametrize(
    ("player_parser"),
    [("Unknown-1234")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_unknown_player_parser_blizzard_error(
    player_parser: PlayerParser,
    player_search_response_mock: Mock,
):
    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=player_search_response_mock,
        ),
    ):
        await player_parser.parse()


@pytest.mark.parametrize(
    ("player_parser", "player_html_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_parser_parsing_error_attribute_error(
    player_parser: PlayerParser,
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
        await player_parser.parse()

    assert (
        error.value.message
        == "AttributeError(\"'NoneType' object has no attribute 'find'\")"
    )


@pytest.mark.parametrize(
    ("player_parser", "player_html_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_parser_parsing_error_key_error(
    player_parser: PlayerParser,
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
        await player_parser.parse()

    assert error.value.message == "KeyError('src')"


@pytest.mark.parametrize(
    ("player_parser", "player_html_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_parser_parsing_error_type_error(
    player_parser: PlayerParser,
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
        await player_parser.parse()

    assert (
        error.value.message == "TypeError(\"'NoneType' object is not subscriptable\")"
    )
