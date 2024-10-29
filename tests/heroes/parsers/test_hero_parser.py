from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.config import settings
from app.enums import Locale
from app.exceptions import OverfastError, ParserBlizzardError
from app.heroes.enums import HeroKey
from app.heroes.parsers.hero_parser import HeroParser


@pytest.mark.parametrize(
    ("hero_key", "hero_html_data"),
    [(h.value, h.value) for h in HeroKey],
    indirect=["hero_html_data"],
)
@pytest.mark.asyncio
async def test_hero_page_parsing(hero_parser: HeroParser, hero_key: str, hero_html_data: str):
    if not hero_html_data:
        pytest.skip("Hero HTML file not saved yet, skipping")

    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=hero_html_data),
    ):
        try:
            await hero_parser.parse()
        except OverfastError:
            pytest.fail(f"Hero page parsing failed for '{hero_key}' hero")


@pytest.mark.parametrize("hero_html_data", ["unknown-hero"], indirect=True)
@pytest.mark.asyncio
async def test_not_released_hero_parser_blizzard_error(hero_parser: HeroParser, hero_html_data: str):
    with (
        pytest.raises(ParserBlizzardError),
        patch(
            "httpx.AsyncClient.get",
            return_value=Mock(status_code=status.HTTP_404_NOT_FOUND, text=hero_html_data),
        ),
    ):
        await hero_parser.parse()

@pytest.mark.parametrize(
    ("url", "full_url"),
    [
        (
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
        ),
        ("/media/stories/bastet", f"{settings.blizzard_host}/media/stories/bastet"),
    ],
)
def test_get_full_url(hero_parser: HeroParser, url: str, full_url: str):
    assert hero_parser._HeroParser__get_full_url(url) == full_url


@pytest.mark.parametrize(
    ("input_str", "locale", "result"),
    [
        # Classic cases
        ("Aug 19 (Age: 37)", Locale.ENGLISH_US, ("Aug 19", 37)),
        ("May 9 (Age: 1)", Locale.ENGLISH_US, ("May 9", 1)),
        # Specific unknown case (bastion)
        ("Unknown (Age: 32)", Locale.ENGLISH_US, (None, 32)),
        # Specific venture case (not the same spacing)
        ("Aug 6 (Age : 26)", Locale.ENGLISH_US, ("Aug 6", 26)),
        ("Aug 6 (Age : 26)", Locale.ENGLISH_EU, ("Aug 6", 26)),
        # Other languages than english
        ("6. Aug. (Alter: 26)", Locale.GERMAN, ("6. Aug.", 26)),
        ("6 ago (Edad: 26)", Locale.SPANISH_EU, ("6 ago", 26)),
        ("6 ago (Edad: 26)", Locale.SPANISH_LATIN, ("6 ago", 26)),
        ("6 août (Âge : 26 ans)", Locale.FRENCH, ("6 août", 26)),
        ("6 ago (Età: 26)", Locale.ITALIANO, ("6 ago", 26)),
        ("8月6日 （年齢: 26）", Locale.JAPANESE, ("8月6日", 26)),
        ("8월 6일 (나이: 26세)", Locale.KOREAN, ("8월 6일", 26)),
        ("6 sie (Wiek: 26 lat)", Locale.POLISH, ("6 sie", 26)),
        ("6 de ago. (Idade: 26)", Locale.PORTUGUESE_BRAZIL, ("6 de ago.", 26)),
        ("6 авг. (Возраст: 26)", Locale.RUSSIAN, ("6 авг.", 26)),
        ("8月6日 （年齡：26）", Locale.CHINESE_TAIWAN, ("8月6日", 26)),
        # Invalid case
        ("Unknown", Locale.ENGLISH_US, (None, None)),
    ],
)
def test_get_birthday_and_age(
    hero_parser: HeroParser, input_str: str, locale: Locale, result: tuple[str | None, int | None]
):
    """Get birthday and age from text for a given hero"""
    assert hero_parser._HeroParser__get_birthday_and_age(input_str, locale) == result
