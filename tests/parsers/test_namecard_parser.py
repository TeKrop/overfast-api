import json
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import HTTPException, status

from app.common.enums import SearchDataType
from app.common.exceptions import ParserParsingError
from app.common.helpers import overfast_client
from app.parsers.search_data_parser import NamecardParser


@pytest.mark.asyncio()
async def test_namecard_parser_no_cache(
    search_players_blizzard_json_data: dict,
    search_html_data: str,
    search_data_json_data: dict,
):
    parser = NamecardParser(player_id="Dekk-2677")
    update_parser_cache_last_update_mock = Mock()

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
    ), patch.object(
        parser.cache_manager,
        "update_parser_cache_last_update",
        update_parser_cache_last_update_mock,
    ):
        await parser.parse()

    assert parser.data == {
        "namecard": search_data_json_data[SearchDataType.NAMECARD]["0x0250000000005510"]
    }
    update_parser_cache_last_update_mock.assert_called_once()


@pytest.mark.asyncio()
async def test_namecard_parser_blizzard_error():
    parser = NamecardParser(player_id="Dekk-2677")

    with pytest.raises(HTTPException) as error, patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        await parser.parse()

    assert error.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert (
        error.value.detail
        == "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    )


@pytest.mark.asyncio()
async def test_namecard_parser_error_key_error(search_tekrop_blizzard_json_data: dict):
    # Search data without battletag
    search_data = [search_tekrop_blizzard_json_data[0].copy()]
    del search_data[0]["battleTag"]

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
        await parser.parse()

    assert error.value.message == "KeyError('battleTag')"


@pytest.mark.asyncio()
async def test_namecard_parser_player_not_found():
    parser = NamecardParser(player_id="Unknown-1234")

    logger_warning_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=status.HTTP_200_OK, text="{}", json=lambda: {}),
    ), patch("app.common.logging.logger.warning", logger_warning_mock):
        await parser.parse()

    logger_warning_mock.assert_any_call(
        "Player {} not found in search results, couldn't retrieve its {}",
        "Unknown-1234",
        SearchDataType.NAMECARD,
    )

    assert parser.data == {"namecard": None}


@pytest.mark.asyncio()
async def test_namecard_parser_player_without_namecard():
    search_data = [
        {
            "battleTag": "Dekk#2677",
            "frame": "0x0250000000000FC1",
            "isPublic": True,
            "lastUpdated": 1678488893,
            "namecard": "0x0000000000000000",
            "portrait": "0x0250000000001598",
            "title": "0x025000000000555E",
        },
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
        await parser.parse()

    logger_info_mock.assert_any_call(
        "Player {} doesn't have any {}", "Dekk-2677", SearchDataType.NAMECARD
    )

    assert parser.data == {"namecard": None}


@pytest.mark.asyncio()
async def test_namecard_parser_no_cache_no_namecard(
    search_players_blizzard_json_data: dict,
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
        "app.common.logging.logger.warning",
        logger_warning_mock,
    ):
        await parser.parse()

    logger_warning_mock.assert_any_call(
        "URL for {} {} of player {} not found in the cache",
        SearchDataType.NAMECARD,
        "0x0250000000005510",
        "Dekk-2677",
    )

    logger_warning_mock.assert_any_call(
        "URL for {} {} of player {} not found at all",
        SearchDataType.NAMECARD,
        "0x0250000000005510",
        "Dekk-2677",
    )

    assert parser.data == {"namecard": None}


@pytest.mark.asyncio()
async def test_namecard_parser_with_cache(
    search_players_blizzard_json_data: dict,
    search_data_json_data: dict,
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
    ), patch.object(
        parser.cache_manager,
        "get_search_data_cache",
        return_value="https://d15f34w2p8l1cc.cloudfront.net/overwatch/757219956129146d84617a7e713dfca1bc33ea27cf6c73df60a33d02a147edc1.png",
    ):
        await parser.parse()

    assert parser.data == {
        "namecard": search_data_json_data[SearchDataType.NAMECARD]["0x0250000000005510"]
    }
