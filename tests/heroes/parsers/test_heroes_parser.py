from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import OverfastError
from app.heroes.enums import HeroKey
from app.heroes.parsers.heroes_parser import HeroesParser


@pytest.mark.asyncio
async def test_heroes_page_parsing(heroes_parser: HeroesParser, heroes_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        try:
            await heroes_parser.parse()
        except OverfastError:
            pytest.fail("Heroes list parsing failed")

    assert all(hero["key"] in iter(HeroKey) for hero in heroes_parser.data)
