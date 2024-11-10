import pytest

from tests.helpers import read_html_file


@pytest.fixture(scope="package")
def home_html_data():
    return read_html_file("home.html")
