import json
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status

from app.exceptions import ParserParsingError
from app.players.enums import SearchDataType
from app.players.parsers.search_data_parser import NamecardParser
from tests.helpers import unknown_player_id


@pytest.mark.parametrize(
    ("namecard_parser"),
    [("TeKrop-2217")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_no_cache(
    namecard_parser: NamecardParser,
    player_search_response_mock: Mock,
):
    with patch(
        "httpx.AsyncClient.get",
        return_value=player_search_response_mock,
    ):
        await namecard_parser.parse()

    assert namecard_parser.data == {"namecard": None}


@pytest.mark.parametrize(
    ("namecard_parser"),
    [("TeKrop-2217")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_blizzard_error(namecard_parser: NamecardParser):
    with (
        pytest.raises(HTTPException) as error,
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                text="Service Unavailable",
            ),
        ),
    ):
        await namecard_parser.parse()

    assert error.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert (
        error.value.detail
        == "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    )


@pytest.mark.parametrize(
    ("namecard_parser"),
    [("TeKrop-2217")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_error_key_error(
    namecard_parser: NamecardParser, search_players_blizzard_json_data: dict
):
    # Search data without battletag
    search_data = [search_players_blizzard_json_data[1].copy()]
    del search_data[0]["battleTag"]

    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(
                status_code=status.HTTP_200_OK,
                text=json.dumps(search_data),
                json=lambda: search_data,
            ),
        ),
        pytest.raises(ParserParsingError) as error,
    ):
        await namecard_parser.parse()

    assert error.value.message == "KeyError('battleTag')"


@pytest.mark.parametrize(
    ("namecard_parser"),
    [(unknown_player_id)],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_player_not_found(namecard_parser: NamecardParser):
    logger_warning_mock = Mock()
    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(status_code=status.HTTP_200_OK, text="{}", json=dict),
        ),
        patch("app.overfast_logger.logger.warning", logger_warning_mock),
    ):
        await namecard_parser.parse()

    logger_warning_mock.assert_any_call(
        "Player {} not found in search results, couldn't retrieve its {}",
        unknown_player_id,
        SearchDataType.NAMECARD,
    )

    assert namecard_parser.data == {"namecard": None}


@pytest.mark.parametrize(
    ("namecard_parser"),
    [("TeKrop-2217")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_player_without_namecard(namecard_parser: NamecardParser):
    search_data = [
        {
            "battleTag": "TeKrop#2217",
            "frame": "0x0250000000000FC1",
            "isPublic": True,
            "lastUpdated": 1678488893,
            "namecard": "0x0000000000000000",
            "portrait": "0x0250000000001598",
            "title": "0x025000000000555E",
        },
    ]

    logger_info_mock = Mock()
    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(
                status_code=status.HTTP_200_OK,
                text=json.dumps(search_data),
                json=lambda: search_data,
            ),
        ),
        patch("app.overfast_logger.logger.info", logger_info_mock),
    ):
        await namecard_parser.parse()

    logger_info_mock.assert_any_call(
        "Player {} doesn't have any {}", "TeKrop-2217", SearchDataType.NAMECARD
    )

    assert namecard_parser.data == {"namecard": None}


@pytest.mark.parametrize(
    ("namecard_parser"),
    [("TeKrop-2217")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_no_cache_no_namecard(
    namecard_parser: NamecardParser,
    player_search_response_mock: Mock,
):
    logger_warning_mock = Mock()
    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=player_search_response_mock,
        ),
        patch(
            "app.overfast_logger.logger.warning",
            logger_warning_mock,
        ),
    ):
        await namecard_parser.parse()

    logger_warning_mock.assert_any_call(
        "URL for {} {} of player {} not found at all",
        SearchDataType.NAMECARD,
        "0x02500000000056EA",
        "TeKrop-2217",
    )

    assert namecard_parser.data == {"namecard": None}


@pytest.mark.parametrize(
    ("namecard_parser"),
    [("TeKrop-2217")],
    indirect=True,
)
@pytest.mark.asyncio
async def test_namecard_parser_with_cache(
    namecard_parser: NamecardParser,
    player_search_response_mock: Mock,
    search_data_json_data: dict,
):
    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=player_search_response_mock,
        ),
        patch.object(
            namecard_parser.cache_manager,
            "get_search_data_cache",
            return_value="https://d15f34w2p8l1cc.cloudfront.net/overwatch/52ee742d4e2fc734e3cd7fdb74b0eac64bcdf26d58372a503c712839595802c5.png",
        ),
    ):
        await namecard_parser.parse()

    assert namecard_parser.data == {
        "namecard": search_data_json_data[SearchDataType.NAMECARD]["0x02500000000056EA"]
    }
