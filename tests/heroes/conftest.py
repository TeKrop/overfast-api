import pytest
from _pytest.fixtures import SubRequest

from tests.helpers import read_html_file


@pytest.fixture(scope="package")
def heroes_html_data():
    return read_html_file("heroes.html")


@pytest.fixture(scope="package")
def hero_html_data(request: SubRequest):
    return read_html_file(f"heroes/{request.param}.html")
