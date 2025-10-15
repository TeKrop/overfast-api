import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from fastapi import status

from tests.helpers import read_html_file, read_json_file

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest


@pytest.fixture(scope="package")
def heroes_html_data():
    return read_html_file("heroes.html")


@pytest.fixture(scope="package")
def hero_html_data(request: SubRequest):
    return read_html_file(f"heroes/{request.param}.html")


@pytest.fixture(scope="package")
def hero_stats_json_data() -> list[dict]:
    return read_json_file("blizzard_hero_stats.json")


@pytest.fixture(scope="package")
def hero_stats_response_mock(hero_stats_json_data: list[dict]) -> Mock:
    return Mock(
        status_code=status.HTTP_200_OK,
        text=json.dumps(hero_stats_json_data),
        json=lambda: hero_stats_json_data,
    )
