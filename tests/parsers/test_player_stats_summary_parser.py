from unittest.mock import Mock, patch

import httpx
import pytest

from app.common.exceptions import ParserBlizzardError
from app.common.helpers import players_ids
from app.parsers.player_stats_summary_parser import PlayerStatsSummaryParser


@pytest.mark.parametrize(
    ("player_id", "player_html_data", "player_stats_json_data"),
    [
        (player_id, player_id, player_id)
        for player_id in players_ids
        if player_id != "Unknown-1234"
    ],
    indirect=["player_html_data", "player_stats_json_data"],
)
@pytest.mark.asyncio
async def test_player_page_parsing(
    player_id: str,
    player_html_data: str,
    player_stats_json_data: dict,
):
    client = httpx.AsyncClient()
    parser = PlayerStatsSummaryParser(client=client, player_id=player_id)
    update_parser_cache_last_update_mock = Mock()

    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(status_code=200, text=player_html_data),
        ),
        patch.object(
            parser.cache_manager,
            "update_parser_cache_last_update",
            update_parser_cache_last_update_mock,
        ),
    ):
        await parser.parse()

    await client.aclose()

    assert parser.data == player_stats_json_data
    update_parser_cache_last_update_mock.assert_called_once()


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
@pytest.mark.asyncio
async def test_unknown_player_parser_blizzard_error(player_html_data: str):
    client = httpx.AsyncClient()
    parser = PlayerStatsSummaryParser(client=client, player_id="Unknown-1234")

    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(status_code=200, text=player_html_data),
        ),
    ):
        await parser.parse()

    await client.aclose()
