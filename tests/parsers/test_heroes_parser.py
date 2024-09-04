from unittest.mock import Mock, patch

import httpx
import pytest

from app.common.enums import HeroKey
from app.common.exceptions import OverfastError
from app.parsers.heroes_parser import HeroesParser


@pytest.mark.asyncio
async def test_heroes_page_parsing(heroes_html_data: str):
    client = httpx.AsyncClient()
    parser = HeroesParser(client=client)

    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=200, text=heroes_html_data),
    ):
        try:
            await parser.parse()
        except OverfastError:
            pytest.fail("Heroes list parsing failed")
        finally:
            await client.aclose()

    assert all(hero["key"] in iter(HeroKey) for hero in parser.data)
