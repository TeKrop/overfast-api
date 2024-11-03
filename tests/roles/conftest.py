import pytest

from tests.helpers import read_html_file, read_json_file


@pytest.fixture(scope="package")
def home_html_data():
    return read_html_file("home.html")


@pytest.fixture(scope="package")
def roles_json_data():
    return read_json_file("roles.json")
