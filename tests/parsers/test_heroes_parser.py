from unittest.mock import Mock, patch

from overfastapi.common.helpers import overfast_client
from overfastapi.parsers.heroes_parser import HeroesParser


def test_heroes_page_parsing(heroes_html_data: str, heroes_json_data: list):
    parser = HeroesParser()

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=heroes_html_data),
    ):
        parser.parse()

    assert parser.data == heroes_json_data
