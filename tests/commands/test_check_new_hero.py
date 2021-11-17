# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest

from overfastapi.commands.check_new_hero import main as check_new_hero_main
from overfastapi.common.enums import HeroKey


@pytest.fixture(scope="module", autouse=True)
def setup_check_new_hero_test():
    with patch(
        "overfastapi.commands.check_new_hero.DISCORD_WEBHOOK_ENABLED",
        return_value=True,
    ):
        yield


def test_check_no_new_hero(heroes_html_data: str):
    logger_info_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=heroes_html_data,
        ),
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_new_hero_main()

    logger_info_mock.assert_called_with("No new hero found. Exiting.")


def test_check_discord_webhook_disabled():
    logger_info_mock = Mock()
    with patch(
        "overfastapi.commands.check_new_hero.DISCORD_WEBHOOK_ENABLED", False
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock), pytest.raises(
        SystemExit
    ):
        check_new_hero_main()

    logger_info_mock.assert_called_with("No Discord webhook configured ! Exiting...")


@pytest.mark.parametrize(
    "distant_heroes,expected",
    [
        ({"one_new_hero"}, {"one_new_hero"}),
        ({"one_new_hero", "two_new_heroes"}, {"one_new_hero", "two_new_heroes"}),
        ({"tracer", "one_new_hero"}, {"one_new_hero"}),
    ],
)
def test_check_new_heroes(distant_heroes: set[str], expected: set[str]):
    logger_info_mock = Mock()
    with patch(
        "overfastapi.commands.check_new_hero.get_distant_hero_keys",
        return_value={*HeroKey, *distant_heroes},
    ), patch("overfastapi.common.logging.logger.info", logger_info_mock):
        check_new_hero_main()

    logger_info_mock.assert_called_with("New hero keys were found : {}", str(expected))


def test_check_error_from_blizzard():
    logger_error_mock = Mock()
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=500,
            text="Internal Server Error",
        ),
    ), patch(
        "overfastapi.common.logging.logger.error", logger_error_mock
    ), pytest.raises(
        SystemExit
    ):
        check_new_hero_main()

    logger_error_mock.assert_called_with(
        "Received an error from Blizzard. HTTP {} : {}", 500, "Internal Server Error"
    )
