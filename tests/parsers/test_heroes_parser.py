from unittest.mock import Mock, patch

import pytest

from app.common.enums import HeroKey
from app.common.exceptions import OverfastError
from app.common.helpers import overfast_client
from app.parsers.heroes_parser import HeroesParser


@pytest.mark.asyncio()
async def test_heroes_page_parsing(heroes_html_data: str):
    parser = HeroesParser()

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=heroes_html_data),
    ):
        try:
            await parser.parse()
        except OverfastError:
            pytest.fail("Heroes list parsing failed")

    assert all(hero["key"] in iter(HeroKey) for hero in parser.data)
