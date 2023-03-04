import asyncio
from unittest.mock import Mock, patch

import pytest

from overfastapi.common.enums import HeroKey
from overfastapi.common.helpers import overfast_client
from overfastapi.parsers.hero_parser import HeroParser


@pytest.mark.parametrize(
    ("hero_html_data", "hero_json_data"),
    [(h.value, h.value) for h in HeroKey],
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
