from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import ParserBlizzardError
from app.players.parsers.player_stats_summary_parser import PlayerStatsSummaryParser
from tests.helpers import players_ids, unknown_player_id


@pytest.mark.parametrize(
    ("player_stats_summary_parser", "player_html_data"),
    [(player_id, player_id) for player_id in players_ids],
    indirect=[
        "player_stats_summary_parser",
        "player_html_data",
    ],
)
@pytest.mark.asyncio
async def test_player_page_parsing(
    player_stats_summary_parser: PlayerStatsSummaryParser,
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
        await player_stats_summary_parser.parse()

    assert len(player_stats_summary_parser.data.keys()) > 0


@pytest.mark.parametrize(
    ("player_stats_summary_parser"),
    [(unknown_player_id)],
    indirect=True,
)
@pytest.mark.asyncio
async def test_unknown_player_parser_blizzard_error(
    player_stats_summary_parser: PlayerStatsSummaryParser,
    player_search_response_mock: Mock,
):
    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=player_search_response_mock,
        ),
    ):
        await player_stats_summary_parser.parse()
