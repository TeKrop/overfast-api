import re
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import ParserBlizzardError, ParserParsingError
from app.players.enums import PlayerGamemode, PlayerPlatform
from tests.helpers import players_ids, unknown_player_id

if TYPE_CHECKING:
    from app.players.parsers.player_career_parser import PlayerCareerParser


@pytest.mark.parametrize(
    ("player_career_parser", "player_html_data", "kwargs_filter"),
    [
        (player_id, player_id, kwargs_filter)
        for player_id in players_ids
        for kwargs_filter in ({}, {"summary": True}, {"stats": True})
    ],
    indirect=["player_career_parser", "player_html_data"],
)
@pytest.mark.asyncio
async def test_player_page_parsing_with_filters(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    kwargs_filter: dict,
    player_search_response_mock: Mock,
):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        await player_career_parser.parse()

    # Just check that the parsing is working properly
    player_career_parser.filter_request_using_query(**kwargs_filter)

    if kwargs_filter.get("summary"):
        assert "summary" in player_career_parser.data
    elif kwargs_filter.get("stats"):
        assert "stats" in player_career_parser.data
    else:
        assert player_career_parser.data.keys() == {"stats", "summary"}


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
):
    player_career_parser._init_filters(platform=platform, gamemode=gamemode)

    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        await player_career_parser.parse()

    # Just check that the parsing is working properly
    filtered_data = player_career_parser._filter_all_stats_data()

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
    ("player_career_parser", "player_html_data"),
    [(unknown_player_id, unknown_player_id)],
    indirect=True,
)
@pytest.mark.asyncio
async def test_unknown_player_career_parser_blizzard_error(
    player_career_parser: PlayerCareerParser,
    player_html_data: str,
    player_search_response_mock: Mock,
):
    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_html_data),
            ],
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
        pytest.raises(
            ParserParsingError,
            match=re.escape(
                "AttributeError(\"'NoneType' object has no attribute 'css_first'\")"
            ),
        ),
    ):
        await player_career_parser.parse()


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
        pytest.raises(ParserParsingError, match=re.escape("KeyError('src')")),
    ):
        await player_career_parser.parse()
