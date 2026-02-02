import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from fastapi import status

from tests.helpers import read_html_file, read_json_file

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest


@pytest.fixture(scope="package")
def player_html_data(request: SubRequest) -> str | None:
    return read_html_file(f"players/{request.param}.html")


@pytest.fixture(scope="package")
def search_players_blizzard_json_data() -> list[dict]:
    json_data = read_json_file("search_players_blizzard_result.json")
    return json_data if isinstance(json_data, list) else []


@pytest.fixture(scope="package")
def player_search_response_mock(search_players_blizzard_json_data: list[dict]) -> Mock:
    return Mock(
        status_code=status.HTTP_200_OK,
        text=json.dumps(search_players_blizzard_json_data),
        json=lambda: search_players_blizzard_json_data,
    )
