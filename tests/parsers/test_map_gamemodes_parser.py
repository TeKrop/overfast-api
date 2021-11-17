# pylint: disable=C0114,C0116
from overfastapi.parsers.map_gamemodes_parser import MapGamemodesParser


def test_maps_page_parsing(maps_html_data: str, map_gamemodes_json_data: list):
    parser = MapGamemodesParser(maps_html_data)
    assert parser.hash == "39b2a22fdab598639efcef5d48a807a5"

    parser.parse()
    assert parser.data == map_gamemodes_json_data
