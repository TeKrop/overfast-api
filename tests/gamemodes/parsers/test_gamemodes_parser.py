import pytest

from app.exceptions import OverfastError
from app.gamemodes.parsers.gamemodes_parser import GamemodesParser


@pytest.mark.asyncio
async def test_gamemodes_page_parsing(gamemodes_parser: GamemodesParser):
    try:
        await gamemodes_parser.parse()
    except OverfastError:
        pytest.fail("Game modes list parsing failed")
