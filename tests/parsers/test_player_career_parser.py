from unittest.mock import Mock, patch

import pytest

from app.common.exceptions import ParserBlizzardError
from app.common.helpers import overfast_client, players_ids
from app.parsers.player_career_parser import PlayerCareerParser


@pytest.mark.parametrize(
    ("player_id", "player_html_data", "player_career_json_data"),
    [
        (player_id, player_id, player_id)
        for player_id in players_ids
        if player_id != "Unknown-1234"
    ],
    indirect=["player_html_data", "player_career_json_data"],
)
@pytest.mark.asyncio()
async def test_player_page_parsing_with_filters(
    player_id: str,
    player_html_data: str,
    player_career_json_data: dict,
):
    parser = PlayerCareerParser(player_id=player_id)
    update_parser_cache_last_update_mock = Mock()

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_html_data),
    ), patch.object(
        parser.cache_manager,
        "update_parser_cache_last_update",
        update_parser_cache_last_update_mock,
    ):
        await parser.parse()

    # Just check that the parsing is working properly
    parser.filter_request_using_query()

    assert parser.data == player_career_json_data
    update_parser_cache_last_update_mock.assert_called_once()


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
@pytest.mark.asyncio()
async def test_unknown_player_parser_blizzard_error(player_html_data: str):
    parser = PlayerCareerParser(player_id="Unknown-1234")
    with pytest.raises(ParserBlizzardError), patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        await parser.parse()
