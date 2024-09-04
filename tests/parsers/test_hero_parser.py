from unittest.mock import Mock, patch

import httpx
import pytest

from app.common.enums import HeroKey
from app.common.exceptions import OverfastError, ParserBlizzardError
from app.parsers.hero_parser import HeroParser


@pytest.mark.parametrize(
    ("hero_key", "hero_html_data"),
    [(h.value, h.value) for h in HeroKey],
    indirect=["hero_html_data"],
)
@pytest.mark.asyncio
async def test_hero_page_parsing(hero_key: str, hero_html_data: str):
    if not hero_html_data:
        pytest.skip("Hero HTML file not saved yet, skipping")

    client = httpx.AsyncClient()
    parser = HeroParser(client=client)

    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=200, text=hero_html_data),
    ):
        try:
            await parser.parse()
        except OverfastError:
            pytest.fail(f"Hero page parsing failed for '{hero_key}' hero")
        finally:
            await client.aclose()


@pytest.mark.parametrize("hero_html_data", ["unknown-hero"], indirect=True)
@pytest.mark.asyncio
async def test_not_released_hero_parser_blizzard_error(hero_html_data: str):
    client = httpx.AsyncClient()
    parser = HeroParser(client=client)

    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(status_code=404, text=hero_html_data),
        ),
    ):
        await parser.parse()

    await client.aclose()
