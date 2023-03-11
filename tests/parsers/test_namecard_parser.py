import asyncio
import json
import re
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import status

from app.common.exceptions import ParserBlizzardError, ParserParsingError
from app.common.helpers import overfast_client
from app.parsers.namecard_parser import NamecardParser


def test_namecard_parser_no_cache(
    search_players_blizzard_json_data: dict,
    search_html_data: str,
    namecards_json_data: dict,
):
    parser = NamecardParser(player_id="Dekk-2677")

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_200_OK,
            text=json.dumps(search_players_blizzard_json_data),
            json=lambda: search_players_blizzard_json_data,
        ),
    ), patch(
        "httpx.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=search_html_data),
    ):
        asyncio.run(parser.parse())

    assert parser.data == {"namecard": namecards_json_data.get("0x0250000000005510")}


def test_namecard_parser_error_key_error():
    # Search data without battletag
    search_data = [
        {
            "frame": "0x0250000000000FC1",
            "isPublic": True,
            "lastUpdated": 1678488893,
            "namecard": "0x0250000000005510",
            "portrait": "0x0250000000001598",
            "title": "0x025000000000555E",
        }
    ]
    parser = NamecardParser(player_id="TeKrop-2217")

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_200_OK,
            text=json.dumps(search_data),
            json=lambda: search_data,
        ),
    ), pytest.raises(ParserParsingError) as error:
        asyncio.run(parser.parse())

    assert error.value.message == "KeyError('battleTag')"


def test_namecard_parser_player_not_found():
    parser = NamecardParser(player_id="Unknown-1234")

    logger_warning_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=status.HTTP_200_OK, text="{}", json=lambda: {}),
    ), patch("app.common.logging.logger.warning", logger_warning_mock):
        asyncio.run(parser.parse())

    logger_warning_mock.assert_any_call(
        "Player {} not found in search results, couldn't retrieve its namecard",
        "Unknown-1234",
    )

    assert parser.data == {"namecard": None}


def test_namecard_parser_player_without_namecard():
    search_data = [
        {
            "battleTag": "Dekk#2677",
            "frame": "0x0250000000000FC1",
            "isPublic": True,
            "lastUpdated": 1678488893,
            "namecard": "0x0000000000000000",
            "portrait": "0x0250000000001598",
            "title": "0x025000000000555E",
        }
    ]
    parser = NamecardParser(player_id="Dekk-2677")

    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_200_OK,
            text=json.dumps(search_data),
            json=lambda: search_data,
        ),
    ), patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(parser.parse())

    logger_info_mock.assert_any_call("Player {} doesn't have any namecard", "Dekk-2677")

    assert parser.data == {"namecard": None}


def test_namecard_parser_no_cache_no_namecard(
    search_players_blizzard_json_data: dict,
    search_html_data: str,
    namecards_json_data: dict,
):
    parser = NamecardParser(player_id="Dekk-2677")

    logger_warning_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_200_OK,
            text=json.dumps(search_players_blizzard_json_data),
            json=lambda: search_players_blizzard_json_data,
        ),
    ), patch("httpx.get", side_effect=httpx.RequestError("error")), patch(
        "app.common.logging.logger.warning", logger_warning_mock
    ):
        asyncio.run(parser.parse())

    logger_warning_mock.assert_any_call(
        "URL for namecard {} of player {} not found in the cache",
        "0x0250000000005510",
        "Dekk-2677",
    )

    logger_warning_mock.assert_any_call(
        "URL for namecard {} of player {} not found at all",
        "0x0250000000005510",
        "Dekk-2677",
    )

    assert parser.data == {"namecard": None}


def test_namecard_parser_with_cache(
    search_players_blizzard_json_data: dict,
    search_html_data: str,
    namecards_json_data: dict,
):
    parser = NamecardParser(player_id="Dekk-2677")
    parser.cache_manager.get_namecard_cache = Mock(
        return_value="https://d15f34w2p8l1cc.cloudfront.net/overwatch/757219956129146d84617a7e713dfca1bc33ea27cf6c73df60a33d02a147edc1.png"
    )

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_200_OK,
            text=json.dumps(search_players_blizzard_json_data),
            json=lambda: search_players_blizzard_json_data,
        ),
    ):
        asyncio.run(parser.parse())

    assert parser.data == {"namecard": namecards_json_data.get("0x0250000000005510")}
