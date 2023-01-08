from unittest.mock import Mock, patch

import pytest

from overfastapi.common.exceptions import ParserInitError
from overfastapi.common.helpers import players_ids
from overfastapi.parsers.player_stats_summary_parser import PlayerStatsSummaryParser


@pytest.mark.parametrize(
    "player_id,player_html_data,player_stats_json_data",
    [
        (player_id, player_id, player_id)
        for player_id in players_ids
        if player_id != "Unknown-1234"
    ],
    indirect=["player_html_data", "player_stats_json_data"],
)
def test_player_page_parsing(
    player_id: str, player_html_data: str, player_stats_json_data: dict
):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        parser = PlayerStatsSummaryParser(player_id=player_id)
    parser.parse()

    assert parser.data == player_stats_json_data


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_unknown_player_parser_init_error(player_html_data: str):
    with pytest.raises(ParserInitError):
        with patch(
            "requests.get",
            return_value=Mock(status_code=200, text=player_html_data),
        ):
            PlayerStatsSummaryParser(player_id="Unknown-1234")
