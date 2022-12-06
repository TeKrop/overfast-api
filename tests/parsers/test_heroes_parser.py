from unittest.mock import Mock, patch

from overfastapi.parsers.heroes_parser import HeroesParser


def test_heroes_page_parsing(heroes_html_data: str, heroes_json_data: list):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=heroes_html_data),
    ):
        parser = HeroesParser()
    assert parser.hash == "fbb263bf3226f784c841d3d5964474cc"

    parser.parse()
    assert parser.data == heroes_json_data
