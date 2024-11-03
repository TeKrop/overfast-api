import pytest

from app.gamemodes.parsers.gamemodes_parser import GamemodesParser


@pytest.fixture(scope="package")
def gamemodes_parser() -> GamemodesParser:
    return GamemodesParser()
