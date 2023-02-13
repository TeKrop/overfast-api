import re
from unittest.mock import Mock, patch

import pytest

from overfastapi.common.exceptions import ParserBlizzardError, ParserParsingError
from overfastapi.common.helpers import players_ids
from overfastapi.parsers.player_parser import PlayerParser


@pytest.mark.parametrize(
    "player_id,player_html_data,player_json_data,kwargs_filter",
    [
        (player_id, player_id, player_id, kwargs_filter)
        for player_id in players_ids
        for kwargs_filter in ({}, {"summary": True}, {"stats": True})
        if player_id != "Unknown-1234"
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_player_page_parsing_with_filters(
    player_id: str,
    player_html_data: str,
    player_json_data: dict,
    kwargs_filter: dict,
):
    parser = PlayerParser(player_id=player_id)

    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        parser.parse()

    # Just check that the parsing is working properly
    parser.filter_request_using_query(**kwargs_filter)

    assert parser.data == player_json_data


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_unknown_player_parser_blizzard_error(player_html_data: str):
    parser = PlayerParser(player_id="Unknown-1234")
    with pytest.raises(ParserBlizzardError), patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        parser.parse()


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error_attribute_error(player_html_data: str):
    with pytest.raises(ParserParsingError) as error:
        player_attr_error = player_html_data.replace(
            'class="Profile-player--summaryWrapper"', 'class="blabla"'
        )
        parser = PlayerParser(player_id="TeKrop-2217")
        with patch(
            "requests.get",
            return_value=Mock(status_code=200, text=player_attr_error),
        ):
            parser.parse()
    assert (
        error.value.message
        == "AttributeError(\"'NoneType' object has no attribute 'find'\")"
    )


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error_key_error(player_html_data: str):
    with pytest.raises(ParserParsingError) as error:
        player_key_error = re.sub(
            'class="Profile-playerSummary--endorsement" src="[^"]*"',
            'class="Profile-playerSummary--endorsement"',
            player_html_data,
        )
        parser = PlayerParser(player_id="TeKrop-2217")
        with patch(
            "requests.get",
            return_value=Mock(status_code=200, text=player_key_error),
        ):
            parser.parse()

    assert error.value.message == "KeyError('src')"


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error_type_error(player_html_data: str):
    with pytest.raises(ParserParsingError) as error:
        player_type_error = player_html_data.replace(
            'class="Profile-playerSummary--endorsement"', ""
        )
        parser = PlayerParser(player_id="TeKrop-2217")
        with patch(
            "requests.get",
            return_value=Mock(status_code=200, text=player_type_error),
        ):
            parser.parse()
    assert (
        error.value.message == "TypeError(\"'NoneType' object is not subscriptable\")"
    )
