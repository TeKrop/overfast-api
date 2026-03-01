import pytest

from tests.helpers import read_html_file


@pytest.fixture(scope="package")
def heroes_html_data() -> str | None:
    return read_html_file("heroes.html")
