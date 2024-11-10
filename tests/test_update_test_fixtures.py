import asyncio
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.config import settings
from app.heroes.enums import HeroKey
from tests.helpers import players_ids
from tests.update_test_fixtures import (  # sourcery skip: dont-import-test-modules
    main as update_test_fixtures_main,
)


@pytest.fixture(scope="module", autouse=True)
def _setup_update_test_fixtures_test():
    with (
        patch(
            "tests.update_test_fixtures.save_fixture_file",
            return_value=Mock(),
        ),
        patch("app.overfast_logger.logger.debug"),
    ):
        yield


test_data_path = f"{settings.test_fixtures_root_path}/html"
heroes_calls = [
    ("Updating {}{}...", test_data_path, "/heroes.html"),
    *[
        ("Updating {}{}...", test_data_path, f"/heroes/{hero.value}.html")
        for hero in HeroKey
    ],
]
players_calls = [
    ("Updating {}{}...", test_data_path, f"/players/{player}.html")
    for player in players_ids
]
home_calls = [("Updating {}{}...", test_data_path, "/home.html")]


@pytest.mark.parametrize(
    ("parameters", "expected_calls"),
    [
        (Mock(heroes=True, home=False, players=False), heroes_calls),
        (Mock(heroes=False, home=True, players=False), home_calls),
        (Mock(heroes=False, home=False, players=True), players_calls),
        (Mock(heroes=True, home=True, players=False), heroes_calls + home_calls),
        (Mock(heroes=True, home=False, players=True), heroes_calls + players_calls),
        (Mock(heroes=False, home=True, players=True), home_calls + players_calls),
        (
            Mock(heroes=True, home=True, players=True),
            heroes_calls + home_calls + players_calls,
        ),
    ],
)
def test_update_with_different_options(parameters, expected_calls: list[str]):
    logger_info_mock = Mock()
    logger_error_mock = Mock()

    with (
        patch(
            "tests.update_test_fixtures.parse_parameters",
            return_value=parameters,
        ),
        patch.object(
            AsyncClient,
            "get",
            return_value=Mock(status_code=status.HTTP_200_OK, text="HTML_DATA"),
        ),
        patch(
            "app.overfast_logger.logger.info",
            logger_info_mock,
        ),
        patch(
            "app.overfast_logger.logger.error",
            logger_error_mock,
        ),
    ):
        asyncio.run(update_test_fixtures_main())

    for expected in expected_calls:
        logger_info_mock.assert_any_call(*expected)
    logger_error_mock.assert_not_called()


def test_update_with_blizzard_error():
    logger_error_mock = Mock()

    with (
        patch(
            "tests.update_test_fixtures.parse_parameters",
            return_value=Mock(heroes=False, players=False, maps=True),
        ),
        patch.object(
            AsyncClient,
            "get",
            return_value=Mock(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                text="BLIZZARD_ERROR",
            ),
        ),
        patch(
            "app.overfast_logger.logger.info",
            Mock(),
        ),
        patch(
            "app.overfast_logger.logger.error",
            logger_error_mock,
        ),
    ):
        asyncio.run(update_test_fixtures_main())

    logger_error_mock.assert_called_with(
        "Error while getting the page : {}",
        "BLIZZARD_ERROR",
    )
