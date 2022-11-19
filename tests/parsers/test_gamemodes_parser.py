from unittest.mock import Mock, patch

from overfastapi.parsers.gamemodes_parser import GamemodesParser


def test_gamemodes_page_parsing(home_html_data: str, gamemodes_json_data: list):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=home_html_data),
    ):
        parser = GamemodesParser()
    assert parser.hash == "ea153ae377336a868a705fa62b3e25cb"

    parser.parse()
    assert parser.data == gamemodes_json_data
