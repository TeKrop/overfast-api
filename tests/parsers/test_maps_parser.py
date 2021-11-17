# pylint: disable=C0114,C0116
from overfastapi.parsers.maps_parser import MapsParser


def test_maps_page_parsing(maps_html_data: str, maps_json_data: list):
    parser = MapsParser(maps_html_data)
    assert parser.hash == "39b2a22fdab598639efcef5d48a807a5"

    parser.parse()
    assert parser.data == maps_json_data
