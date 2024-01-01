from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import status

from app.commands.update_search_data_cache import main as update_search_data_cache_main
from app.common.cache_manager import CacheManager
from app.common.enums import SearchDataType


@pytest.fixture()
def cache_manager():
    return CacheManager()


def test_update_search_data_cache(
    cache_manager: CacheManager,
    search_html_data: str,
    search_data_json_data: dict,
):
    # Nominal case, everything is working fine
    with patch(
        "httpx.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=search_html_data),
    ):
        update_search_data_cache_main()

    assert all(
        cache_manager.get_search_data_cache(data_type, data_key) == data_value
        for data_type, data in search_data_json_data.items()
        for data_key, data_value in data.items()
    )

    assert all(
        cache_manager.get_search_data_cache(data_type, "0x1234") is None
        for data_type in SearchDataType
    )


# RequestError from httpx not saving anything
@pytest.mark.parametrize(("data_type"), list(SearchDataType))
def test_update_search_data_request_error(
    cache_manager: CacheManager, data_type: SearchDataType
):
    cache_manager.update_search_data_cache({data_type: {"fake": "value"}})

    logger_exception_mock = Mock()
    with patch("httpx.get", side_effect=httpx.RequestError("error")), patch(
        "app.common.logging.logger.exception",
        logger_exception_mock,
    ), pytest.raises(SystemExit):
        update_search_data_cache_main()

    logger_exception_mock.assert_any_call(
        "An error occurred while requesting search data !",
    )
    assert cache_manager.get_search_data_cache(data_type, "fake") == "value"


def test_update_search_data_cache_not_found(cache_manager: CacheManager):
    cache_manager.update_search_data_cache({SearchDataType.NAMECARD: {"fake": "value"}})

    logger_exception_mock = Mock()
    with patch(
        "httpx.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text="OK"),
    ), patch(
        "app.common.logging.logger.exception",
        logger_exception_mock,
    ), pytest.raises(
        SystemExit,
    ):
        update_search_data_cache_main()

    logger_exception_mock.assert_any_call("namecard data not found on Blizzard page !")
    assert (
        cache_manager.get_search_data_cache(SearchDataType.NAMECARD, "fake") == "value"
    )


@pytest.mark.parametrize(
    ("data_type", "blizzard_response_text"),
    [
        (
            SearchDataType.NAMECARD,
            (
                'const namecards = {"test":abc}\n'
                'const avatars = {"fake":{"icon":"value"}}\n'
                'const titles = {"fake":{"name":{"en_US":"value"}}}\n'
            ),
        ),
        (
            SearchDataType.PORTRAIT,
            (
                'const namecards = {"fake":{"icon":"value"}}\n'
                'const avatars = {"test":abc}\n'
                'const titles = {"fake":{"name":{"en_US":"value"}}}\n'
            ),
        ),
        (
            SearchDataType.TITLE,
            (
                'const namecards = {"fake":{"icon":"value"}}\n'
                'const avatars = {"fake":{"icon":"value"}}\n'
                'const titles = {"test":abc}\n'
            ),
        ),
    ],
)
def test_update_search_data_cache_invalid_json(
    cache_manager: CacheManager, data_type: SearchDataType, blizzard_response_text: str
):
    cache_manager.update_search_data_cache({data_type: {"fake": "value"}})

    logger_exception_mock = Mock()
    with patch(
        "httpx.get",
        return_value=Mock(
            status_code=status.HTTP_200_OK,
            text=blizzard_response_text,
        ),
    ), patch(
        "app.common.logging.logger.exception",
        logger_exception_mock,
    ), pytest.raises(
        SystemExit,
    ):
        update_search_data_cache_main()

    logger_exception_mock.assert_any_call(
        f"Invalid format for {data_type} data on Blizzard page !",
    )
    assert cache_manager.get_search_data_cache(data_type, "fake") == "value"
