import json
from collections.abc import Callable
from unittest.mock import Mock

import pytest
from _pytest.fixtures import SubRequest
from fastapi import status

from app.players.enums import SearchDataType
from tests.helpers import read_html_file, read_json_file


@pytest.fixture(scope="package")
def player_html_data(request: SubRequest) -> str:
    return read_html_file(f"players/{request.param}.html")


@pytest.fixture(scope="package")
def search_html_data() -> str:
    return read_html_file("search.html")


@pytest.fixture(scope="package")
def search_players_blizzard_json_data() -> list:
    return read_json_file("search_players_blizzard_result.json")


@pytest.fixture(scope="package")
def search_data_json_data() -> list:
    return read_json_file("formatted_search_data.json")


@pytest.fixture(scope="package")
def player_search_response_mock(search_players_blizzard_json_data: dict) -> Mock:
    return Mock(
        status_code=status.HTTP_200_OK,
        text=json.dumps(search_players_blizzard_json_data),
        json=lambda: search_players_blizzard_json_data,
    )


@pytest.fixture(scope="package")
def search_data_func(search_data_json_data: dict) -> Callable[[str, str], str | None]:
    # Inner function that does the lookup
    def get_data(data_type: SearchDataType, cache_key: str) -> str | None:
        return search_data_json_data[data_type].get(cache_key)

    # Return the inner function itself, not the result of calling it
    return get_data
