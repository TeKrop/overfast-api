from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import ParserBlizzardError
from app.players.parsers.player_career_stats_parser import PlayerCareerStatsParser
from tests.helpers import players_ids, unknown_player_id


@pytest.mark.parametrize(
    ("player_career_stats_parser", "player_html_data"),
    [(player_id, player_id) for player_id in players_ids],
    indirect=[
        "player_career_stats_parser",
        "player_html_data",
    ],
)
@pytest.mark.asyncio
async def test_player_page_parsing_with_filters(
    player_career_stats_parser: PlayerCareerStatsParser,
    player_html_data: str,
    player_search_response_mock: Mock,
    blizzard_unlock_response_mock: Mock,
):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Unlocks response
            blizzard_unlock_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        await player_career_stats_parser.parse()

    # Just check that the parsing is working properly
    player_career_stats_parser.filter_request_using_query()

    assert len(player_career_stats_parser.data.keys()) > 0


@pytest.mark.parametrize(
    ("player_career_stats_parser"),
    [(unknown_player_id)],
    indirect=True,
)
@pytest.mark.asyncio
async def test_unknown_player_parser_blizzard_error(
    player_career_stats_parser: PlayerCareerStatsParser,
    player_search_response_mock: Mock,
):
    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=player_search_response_mock,
        ),
    ):
        await player_career_stats_parser.parse()
