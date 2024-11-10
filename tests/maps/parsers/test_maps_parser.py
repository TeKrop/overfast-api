import pytest

from app.exceptions import OverfastError
from app.maps.parsers.maps_parser import MapsParser


@pytest.mark.asyncio
async def test_maps_page_parsing(maps_parser: MapsParser):
    try:
        await maps_parser.parse()
    except OverfastError:
        pytest.fail("Maps list parsing failed")

    # Just check the format of the first map in the list
    assert maps_parser.data[0] == {
        "name": "Hanamura",
        "screenshot": "https://overfast-api.tekrop.fr/static/maps/hanamura.jpg",
        "gamemodes": ["assault"],
        "location": "Tokyo, Japan",
        "country_code": "JP",
    }
