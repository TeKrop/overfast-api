from overfastapi.parsers.maps_parser import MapsParser


def test_maps_page_parsing(maps_json_data: list):
    parser = MapsParser()
    parser.parse()

    assert parser.data == maps_json_data
