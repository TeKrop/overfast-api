import asyncio
import re
from unittest.mock import Mock, patch

import pytest

from app.common.exceptions import ParserBlizzardError, ParserParsingError
from app.common.helpers import overfast_client, players_ids
from app.parsers.player_parser import PlayerParser


@pytest.mark.parametrize(
    ("player_id", "player_html_data", "player_json_data", "kwargs_filter"),
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
    # Remove "namecard" key from player_json_data, it's been added from another page
    player_data = player_json_data.copy()
    del player_data["summary"]["namecard"]

    parser = PlayerParser(player_id=player_id)
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
        asyncio.run(parser.parse())

    # Just check that the parsing is working properly
    parser.filter_request_using_query(**kwargs_filter)

    assert parser.data == player_data
    update_parser_cache_last_update_mock.assert_called_once()


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_unknown_player_parser_blizzard_error(player_html_data: str):
    parser = PlayerParser(player_id="Unknown-1234")
    with pytest.raises(ParserBlizzardError), patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        asyncio.run(parser.parse())


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error_attribute_error(player_html_data: str):
    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"', 'class="blabla"'
    )
    parser = PlayerParser(player_id="TeKrop-2217")

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_attr_error),
    ), pytest.raises(ParserParsingError) as error:
        asyncio.run(parser.parse())

    assert (
        error.value.message
        == "AttributeError(\"'NoneType' object has no attribute 'find'\")"
    )


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error_key_error(player_html_data: str):
    player_key_error = re.sub(
        'class="Profile-playerSummary--endorsement" src="[^"]*"',
        'class="Profile-playerSummary--endorsement"',
        player_html_data,
    )
    parser = PlayerParser(player_id="TeKrop-2217")

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_key_error),
    ), pytest.raises(ParserParsingError) as error:
        asyncio.run(parser.parse())

    assert error.value.message == "KeyError('src')"


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error_type_error(player_html_data: str):
    player_type_error = player_html_data.replace(
        'class="Profile-playerSummary--endorsement"', ""
    )
    parser = PlayerParser(player_id="TeKrop-2217")

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_type_error),
    ), pytest.raises(ParserParsingError) as error:
        asyncio.run(parser.parse())

    assert (
        error.value.message == "TypeError(\"'NoneType' object is not subscriptable\")"
    )
