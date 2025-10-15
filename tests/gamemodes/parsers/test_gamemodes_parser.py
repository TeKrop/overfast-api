from typing import TYPE_CHECKING

import pytest

from app.exceptions import OverfastError

if TYPE_CHECKING:
    from app.gamemodes.parsers.gamemodes_parser import GamemodesParser


@pytest.mark.asyncio
async def test_gamemodes_page_parsing(gamemodes_parser: GamemodesParser):
    try:
        await gamemodes_parser.parse()
    except OverfastError:
        pytest.fail("Game modes list parsing failed")

    # Just check the format of the first gamemode in the list
    assert gamemodes_parser.data[0] == {
        "key": "assault",
        "name": "Assault",
        "icon": "https://overfast-api.tekrop.fr/static/gamemodes/assault-icon.svg",
        "description": "Teams fight to capture or defend two successive points against the enemy team. It's an inactive Overwatch 1 gamemode, also called 2CP.",
        "screenshot": "https://overfast-api.tekrop.fr/static/gamemodes/assault.avif",
    }
