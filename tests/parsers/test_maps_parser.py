import pytest

from app.common.exceptions import OverfastError
from app.parsers.maps_parser import MapsParser


@pytest.mark.asyncio()
async def test_maps_page_parsing():
    parser = MapsParser()

    try:
        await parser.parse()
    except OverfastError:
        pytest.fail("Maps list parsing failed")
