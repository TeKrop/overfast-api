import pytest

from app.common.exceptions import OverfastError
from app.parsers.gamemodes_parser import GamemodesParser


@pytest.mark.asyncio
async def test_gamemodes_page_parsing(home_html_data: str):
    parser = GamemodesParser()

    try:
        await parser.parse()
    except OverfastError:
        pytest.fail("Game modes list parsing failed")
