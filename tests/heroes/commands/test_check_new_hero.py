import asyncio
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.heroes.commands.check_new_hero import main as check_new_hero_main
from app.heroes.enums import HeroKey


@pytest.fixture(scope="module", autouse=True)
def _setup_check_new_hero_test():
    with patch(
        "app.heroes.commands.check_new_hero.settings",
        return_value=Mock(discord_webhook_enabled=True),
    ):
        yield


def test_check_no_new_hero(heroes_html_data: str):
    logger_info_mock = Mock()
    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
        ),
        patch("app.overfast_logger.logger.info", logger_info_mock),
    ):
        asyncio.run(check_new_hero_main())

    logger_info_mock.assert_called_with("No new hero found. Exiting.")


def test_check_discord_webhook_disabled():
    logger_info_mock = Mock()
    with (
        patch(
            "app.heroes.commands.check_new_hero.settings.discord_webhook_enabled",
            False,
        ),
        patch("app.overfast_logger.logger.info", logger_info_mock),
        pytest.raises(
            SystemExit,
        ),
    ):
        asyncio.run(check_new_hero_main())

    logger_info_mock.assert_called_with("No Discord webhook configured ! Exiting...")


@pytest.mark.parametrize(
    ("distant_heroes", "expected"),
    [
        ({"one_new_hero"}, {"one_new_hero"}),
        ({"one_new_hero", "two_new_heroes"}, {"one_new_hero", "two_new_heroes"}),
        ({"tracer", "one_new_hero"}, {"one_new_hero"}),
    ],
)
def test_check_new_heroes(distant_heroes: set[str], expected: set[str]):
    logger_info_mock = Mock()
    with (
        patch(
            "app.heroes.commands.check_new_hero.get_distant_hero_keys",
            return_value={*HeroKey, *distant_heroes},
        ),
        patch("app.overfast_logger.logger.info", logger_info_mock),
    ):
        asyncio.run(check_new_hero_main())

    logger_info_mock.assert_called_with("New hero keys were found : {}", expected)


def test_check_error_from_blizzard():
    logger_error_mock = Mock()
    with (
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                text="Internal Server Error",
            ),
        ),
        patch("app.overfast_logger.logger.error", logger_error_mock),
        pytest.raises(
            SystemExit,
        ),
    ):
        asyncio.run(check_new_hero_main())

    logger_error_mock.assert_called_with(
        "Received an error from Blizzard. HTTP {} : {}",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal Server Error",
    )
