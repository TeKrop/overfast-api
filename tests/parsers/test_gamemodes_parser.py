from unittest.mock import Mock, patch

from overfastapi.parsers.gamemodes_parser import GamemodesParser


def test_gamemodes_page_parsing(home_html_data: str, gamemodes_json_data: list):
    parser = GamemodesParser()

    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=home_html_data),
    ):
        parser.parse()
    assert parser.data == gamemodes_json_data
