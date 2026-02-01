from typing import TYPE_CHECKING

import pytest

from app.exceptions import OverfastError

if TYPE_CHECKING:
    from app.maps.parsers.maps_parser import MapsParser


@pytest.mark.asyncio
async def test_maps_page_parsing(maps_parser: MapsParser):
    try:
        await maps_parser.parse()
    except OverfastError:
        pytest.fail("Maps list parsing failed")

    # Just check the format of the first map in the list
    assert isinstance(maps_parser.data, list)
    assert maps_parser.data[0] == {
        "key": "aatlis",
        "name": "Aatlis",
        "screenshot": "https://overfast-api.tekrop.fr/static/maps/aatlis.jpg",
        "gamemodes": ["flashpoint"],
        "location": "Morocco",
        "country_code": "MA",
    }
