# pylint: disable=C0114,C0116
from overfastapi.parsers.gamemodes_parser import GamemodesParser


def test_gamemodes_page_parsing(home_html_data: str, gamemodes_json_data: list):
    parser = GamemodesParser(home_html_data)
    assert parser.hash == "ea153ae377336a868a705fa62b3e25cb"

    parser.parse()
    assert parser.data == gamemodes_json_data
