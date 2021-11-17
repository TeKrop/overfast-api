# pylint: disable=C0114,C0116
from overfastapi.parsers.heroes_parser import HeroesParser


def test_heroes_page_parsing(heroes_html_data: str, heroes_json_data: list):
    parser = HeroesParser(heroes_html_data)
    assert parser.hash == "5c5dbe354c50edd1c90422005a546c7c"

    parser.parse()
    assert parser.data == heroes_json_data
