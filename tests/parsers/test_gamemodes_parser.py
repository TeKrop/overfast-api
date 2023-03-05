import asyncio
from unittest.mock import Mock, patch

from app.common.helpers import overfast_client
from app.parsers.gamemodes_parser import GamemodesParser


def test_gamemodes_page_parsing(home_html_data: str, gamemodes_json_data: list):
    parser = GamemodesParser()

    with patch.object(
        overfast_client, "get", return_value=Mock(status_code=200, text=home_html_data)
    ):
        asyncio.run(parser.parse())
    assert parser.data == gamemodes_json_data
