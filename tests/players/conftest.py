import json
from unittest.mock import Mock

import pytest
from _pytest.fixtures import SubRequest
from fastapi import status

from tests.helpers import read_html_file, read_json_file


@pytest.fixture(scope="package")
def player_html_data(request: SubRequest) -> str:
    return read_html_file(f"players/{request.param}.html")


@pytest.fixture(scope="package")
def search_players_blizzard_json_data() -> list[dict]:
    return read_json_file("search_players_blizzard_result.json")


@pytest.fixture(scope="package")
def search_data_json_data() -> list:
    return read_json_file("formatted_search_data.json")


@pytest.fixture(scope="package")
def player_search_response_mock(search_players_blizzard_json_data: list[dict]) -> Mock:
    return Mock(
        status_code=status.HTTP_200_OK,
        text=json.dumps(search_players_blizzard_json_data),
        json=lambda: search_players_blizzard_json_data,
    )
