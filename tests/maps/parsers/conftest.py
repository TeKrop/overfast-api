import pytest

from app.maps.parsers.maps_parser import MapsParser


@pytest.fixture(scope="package")
def maps_parser() -> MapsParser:
    return MapsParser()
