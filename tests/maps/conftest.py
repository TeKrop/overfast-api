import pytest

from tests.helpers import read_json_file


@pytest.fixture(scope="package")
def maps_json_data():
    return read_json_file("maps.json")
