from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import status

from app.commands.update_namecards_cache import main as update_namecards_cache_main
from app.common.cache_manager import CacheManager


@pytest.fixture()
def cache_manager():
    return CacheManager()


def test_update_namecards_cache(
    cache_manager: CacheManager,
    search_html_data: str,
    namecards_json_data: dict,
):
    # Nominal case, everything is working fine
    with patch(
        "httpx.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=search_html_data),
    ):
        update_namecards_cache_main()

    for namecard_key, namecard_url in namecards_json_data.items():
        assert cache_manager.get_namecard_cache(namecard_key) == namecard_url
    assert cache_manager.get_namecard_cache("0x1234") is None


# RequestError from httpx not saving anything
def test_update_namecards_request_error(cache_manager: CacheManager):
    cache_manager.update_namecards_cache({"fake": "value"})

    logger_exception_mock = Mock()
    with patch("httpx.get", side_effect=httpx.RequestError("error")), patch(
        "app.common.logging.logger.exception", logger_exception_mock
    ), pytest.raises(SystemExit):
        update_namecards_cache_main()

    logger_exception_mock.assert_any_call(
        "An error occurred while requesting namecards !"
    )
    assert cache_manager.get_namecard_cache("fake") == "value"


def test_update_namecards_cache_namecards_not_found(cache_manager: CacheManager):
    cache_manager.update_namecards_cache({"fake": "value"})

    logger_exception_mock = Mock()
    with patch(
        "httpx.get", return_value=Mock(status_code=status.HTTP_200_OK, text="OK")
    ), patch(
        "app.common.logging.logger.exception", logger_exception_mock
    ), pytest.raises(
        SystemExit
    ):
        update_namecards_cache_main()

    logger_exception_mock.assert_any_call("Namecards not found on Blizzard page !")
    assert cache_manager.get_namecard_cache("fake") == "value"


def test_update_namecards_cache_invalid_json(cache_manager: CacheManager):
    cache_manager.update_namecards_cache({"fake": "value"})

    logger_exception_mock = Mock()
    with patch(
        "httpx.get",
        return_value=Mock(
            status_code=status.HTTP_200_OK, text="const namecards = {'test':abc}\n"
        ),
    ), patch(
        "app.common.logging.logger.exception", logger_exception_mock
    ), pytest.raises(
        SystemExit
    ):
        update_namecards_cache_main()

    logger_exception_mock.assert_any_call(
        "Invalid format for namecards on Blizzard page !"
    )
    assert cache_manager.get_namecard_cache("fake") == "value"
