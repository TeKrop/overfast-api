import pytest

from app.heroes.parsers.hero_parser import HeroParser
from app.heroes.parsers.hero_stats_summary_parser import HeroStatsSummaryParser
from app.heroes.parsers.heroes_parser import HeroesParser
from app.players.enums import PlayerGamemode, PlayerPlatform, PlayerRegion


@pytest.fixture(scope="package")
def hero_parser() -> HeroParser:
    return HeroParser()


@pytest.fixture(scope="package")
def heroes_parser() -> HeroesParser:
    return HeroesParser()


@pytest.fixture(scope="package")
def hero_stats_summary_parser() -> HeroStatsSummaryParser:
    return HeroStatsSummaryParser(
        platform=PlayerPlatform.PC,
        gamemode=PlayerGamemode.COMPETITIVE,
        region=PlayerRegion.EUROPE,
        order_by="hero:asc",
    )
