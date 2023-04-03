import asyncio
from unittest.mock import Mock, patch

import pytest

from app.common.enums import HeroKey
from app.common.exceptions import ParserBlizzardError
from app.common.helpers import overfast_client
from app.parsers.hero_parser import HeroParser


@pytest.mark.parametrize(
    ("hero_html_data", "hero_json_data"),
    [(h.value, h.value) for h in HeroKey if h.value != HeroKey.LIFEWEAVER],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_hero_page_parsing(hero_html_data: str, hero_json_data: dict):
    # Remove "portrait" key from hero_json_data, it's been added from another page
    hero_data = hero_json_data.copy()
    del hero_data["portrait"]

    parser = HeroParser()

    with patch.object(
        overfast_client, "get", return_value=Mock(status_code=200, text=hero_html_data)
    ):
        asyncio.run(parser.parse())

    assert parser.data == hero_data


@pytest.mark.parametrize("hero_html_data", ["unknown-hero"], indirect=True)
def test_not_released_hero_parser_blizzard_error(hero_html_data: str):
    parser = HeroParser()
    with pytest.raises(ParserBlizzardError), patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=404, text=hero_html_data),
    ):
        asyncio.run(parser.parse())
