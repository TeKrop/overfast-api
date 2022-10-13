from unittest.mock import Mock, patch

import pytest
from requests import Session

from overfastapi.commands.update_test_fixtures import main as update_test_fixtures_main
from overfastapi.common.enums import HeroKey
from overfastapi.config import TEST_FIXTURES_ROOT_PATH


@pytest.fixture(scope="module", autouse=True)
def setup_update_test_fixtures_test():
    with patch(
        "overfastapi.commands.update_test_fixtures.save_fixture_file",
        return_value=Mock(),
    ), patch("overfastapi.common.logging.logger.debug"):
        yield


heroes_calls = [
    f"Updating {TEST_FIXTURES_ROOT_PATH}/html/heroes.html...",
    *[
        f"Updating {TEST_FIXTURES_ROOT_PATH}/html/heroes/{hero.value}.html..."
        for hero in HeroKey
    ],
]
players_calls = [
    f"Updating {TEST_FIXTURES_ROOT_PATH}/html/player/{player}.html..."
    for player in [
        "TeKrop-2217",
        "Player-162460",
        "test-1337",
        "Unknown-1234",
        "test-325d682072d7a4c61c33b6bbaa83b859",
        "test-e66c388f13a7f408a6e1738f3d5161e2",
        "xJaymog",
        "Ka1zen_x",
        "mightyy_Brig",
    ]
]
home_calls = [f"Updating {TEST_FIXTURES_ROOT_PATH}/html/home.html..."]


@pytest.mark.parametrize(
    "parameters,expected_calls",
    [
        (Mock(heroes=True, home=False, players=False), heroes_calls),
        (Mock(heroes=False, home=True, players=False), home_calls),
        (Mock(heroes=False, home=False, players=True), players_calls),
        (Mock(heroes=True, home=True, players=False), heroes_calls + home_calls),
        (Mock(heroes=True, home=False, players=True), heroes_calls + players_calls),
        (Mock(heroes=False, home=True, players=True), home_calls + players_calls),
        (
            Mock(heroes=True, home=True, players=True),
            heroes_calls,
            home_calls + players_calls,
        ),
    ],
)
def test_update_with_different_options(parameters, expected_calls: list[str]):
    logger_info_mock = Mock()
    logger_error_mock = Mock()

    with patch(
        "overfastapi.commands.update_test_fixtures.parse_parameters",
        return_value=parameters,
    ), patch.object(
        Session,
        "get",
        return_value=Mock(status_code=200, text="HTML_DATA"),
    ), patch(
        "overfastapi.common.logging.logger.info", logger_info_mock
    ), patch(
        "overfastapi.common.logging.logger.error", logger_error_mock
    ):
        update_test_fixtures_main()

    for expected in expected_calls:
        logger_info_mock.assert_any_call(expected)
    logger_error_mock.assert_not_called()


def test_update_with_blizzard_error():
    logger_error_mock = Mock()

    with patch(
        "overfastapi.commands.update_test_fixtures.parse_parameters",
        return_value=Mock(heroes=False, players=False, maps=True),
    ), patch.object(
        Session,
        "get",
        return_value=Mock(status_code=500, text="BLIZZARD_ERROR"),
    ), patch(
        "overfastapi.common.logging.logger.info", Mock()
    ), patch(
        "overfastapi.common.logging.logger.error", logger_error_mock
    ):
        update_test_fixtures_main()

    logger_error_mock.assert_called_with(
        "Error while getting the page : {}", "BLIZZARD_ERROR"
    )
