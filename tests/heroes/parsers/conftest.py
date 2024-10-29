import pytest

from app.heroes.parsers.hero_parser import HeroParser
from app.heroes.parsers.heroes_parser import HeroesParser


@pytest.fixture(scope="package")
def hero_parser() -> HeroParser:
    return HeroParser()


@pytest.fixture(scope="package")
def heroes_parser() -> HeroesParser:
    return HeroesParser()
