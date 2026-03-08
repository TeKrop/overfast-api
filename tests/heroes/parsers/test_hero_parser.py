"""Tests for _parse_birthday_and_age in app/domain/parsers/hero.py"""

import pytest

from app.domain.enums import Locale
from app.domain.parsers.hero import _parse_birthday_and_age


@pytest.mark.parametrize(
    ("text", "locale", "expected"),
    [
        # en-us / en-gb
        ("Unknown", Locale.ENGLISH_US, (None, None)),
        ("Aug 8 (Age: 22)", Locale.ENGLISH_US, ("Aug 8", 22)),
        ("Aug 28 (Age: 32)", Locale.ENGLISH_US, ("Aug 28", 32)),
        ("Jan 1 (Age: 62)", Locale.ENGLISH_US, ("Jan 1", 62)),
        ("Unknown (Age: 32)", Locale.ENGLISH_US, (None, 32)),
        ("May 9 (Age: 1)", Locale.ENGLISH_US, ("May 9", 1)),
        ("May 9 (Age: 1)", Locale.ENGLISH_EU, ("May 9", 1)),
        # de-de
        ("9. Mai (Alter: 1)", Locale.GERMAN, ("9. Mai", 1)),
        ("Unbekannt (Alter: 32)", Locale.GERMAN, (None, 32)),
        # fr-fr
        ("9 mai (âge : 1 an)", Locale.FRENCH, ("9 mai", 1)),
        ("Inconnu (âge : 32 ans)", Locale.FRENCH, (None, 32)),
        # it-it
        ("9 mag (Età: 1)", Locale.ITALIANO, ("9 mag", 1)),
        # es-es
        ("9 may (Edad: 1)", Locale.SPANISH_EU, ("9 may", 1)),
        # pl-pl
        ("9 maj (Wiek: 1)", Locale.POLISH, ("9 maj", 1)),
        # ja-jp
        ("5月9日 （年齢: 1）", Locale.JAPANESE, ("5月9日", 1)),
        # ru-ru
        ("9 мая (возраст: 1 г.)", Locale.RUSSIAN, ("9 мая", 1)),  # noqa: RUF001
        # ko-kr
        ("5월 9일 (나이: 1)", Locale.KOREAN, ("5월 9일", 1)),
        # zh-tw
        ("5月9日 （年齡：1）", Locale.CHINESE_TAIWAN, ("5月9日", 1)),
        # pt-br
        ("Desconhecido (Idade: 10)", Locale.PORTUGUESE_BRAZIL, ("Unknown", 10)),
    ],
)
def test_parse_birthday_and_age(
    text: str,
    locale: Locale,
    expected: tuple[str | None, int | None],
):
    result = _parse_birthday_and_age(text, locale)

    assert result == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Aug 8",  # date with no parenthetical age block
    ],
)
def test_parse_birthday_and_age_no_match_returns_none_none(text: str):
    result = _parse_birthday_and_age(text, Locale.ENGLISH_US)

    assert result == (None, None)
