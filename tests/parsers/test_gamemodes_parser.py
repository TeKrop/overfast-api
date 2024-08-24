from unittest.mock import Mock, patch

import pytest

from app.common.exceptions import OverfastError
from app.common.helpers import overfast_client
from app.parsers.gamemodes_parser import GamemodesParser


@pytest.mark.asyncio
async def test_gamemodes_page_parsing(home_html_data: str):
    parser = GamemodesParser()

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=home_html_data),
    ):
        try:
            await parser.parse()
        except OverfastError:
            pytest.fail("Game modes list parsing failed")
