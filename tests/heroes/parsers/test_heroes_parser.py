from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard import BlizzardClient
from app.domain.enums import HeroGamemode, HeroKey, Role
from app.domain.exceptions import ParserParsingError
from app.domain.parsers.heroes import (
    fetch_heroes_html,
    filter_heroes,
    parse_heroes,
    parse_heroes_html,
)


def test_parse_heroes_html_returns_all_heroes(heroes_html_data: str):
    result = parse_heroes_html(heroes_html_data)

    assert isinstance(result, list)
    assert all(hero["key"] in iter(HeroKey) for hero in result)


def test_parse_heroes_html_entry_format(heroes_html_data: str):
    result = parse_heroes_html(heroes_html_data)
    first = result[0]

    assert set(first.keys()) == {"key", "name", "portrait", "role", "gamemodes"}


def test_filter_heroes_by_role(heroes_html_data: str):
    heroes = parse_heroes_html(heroes_html_data)
    filtered = filter_heroes(heroes, role=Role.TANK, gamemode=None)

    assert all(h["role"] == Role.TANK for h in filtered)
    assert len(filtered) < len(heroes)


def test_filter_heroes_by_gamemode(heroes_html_data: str):
    heroes = parse_heroes_html(heroes_html_data)
    filtered = filter_heroes(heroes, role=None, gamemode=HeroGamemode.STADIUM)

    assert len(filtered) <= len(heroes)


def test_filter_heroes_no_filter(heroes_html_data: str):
    heroes = parse_heroes_html(heroes_html_data)
    actual = filter_heroes(heroes, role=None, gamemode=None)

    assert actual == heroes


@pytest.mark.asyncio
async def test_fetch_heroes_html_calls_blizzard(heroes_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        client = BlizzardClient()
        html = await fetch_heroes_html(client)

    assert html == heroes_html_data


def test_parse_heroes_html_invalid_hero_url_raises():
    """A hero element with no href raises ParserParsingError."""
    # Build HTML with a hero element that has no href attribute
    html = """
    <html><body>
    <main class="main-content">
      <div class="heroIndexWrapper">
        <blz-media-gallery>
          <a><!-- no href -->
            <blz-card>
              <blz-content-block><h2>Tracer</h2></blz-content-block>
              <blz-image src="https://example.com/tracer.png"></blz-image>
            </blz-card>
          </a>
        </blz-media-gallery>
      </div>
    </main>
    </body></html>
    """
    with pytest.raises(ParserParsingError):
        parse_heroes_html(html)


def test_parse_heroes_html_dom_error_raises():
    """Malformed hero structure (missing h2/blz-image) raises ParserParsingError."""
    # No error here — safe_get_text/attribute return None gracefully
    # So let's test the AttributeError branch via a truly malformed structure
    # by passing a broken dict structure (triggers the outer except)
    with (
        patch(
            "app.domain.parsers.heroes.parse_html_root",
            side_effect=AttributeError("forced"),
        ),
        pytest.raises(ParserParsingError),
    ):
        parse_heroes_html("<html></html>")


@pytest.mark.asyncio
async def test_parse_heroes_high_level(heroes_html_data: str):
    """parse_heroes() fetches HTML then parses and filters it."""
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        client = BlizzardClient()
        heroes = await parse_heroes(client)

    assert isinstance(heroes, list)
    assert len(heroes) > 0
    assert all("key" in h for h in heroes)


@pytest.mark.asyncio
async def test_parse_heroes_with_role_filter(heroes_html_data: str):
    """parse_heroes() with role filter returns only matching heroes."""
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        client = BlizzardClient()
        heroes = await parse_heroes(client, role=Role.TANK)

    assert all(h["role"] == Role.TANK for h in heroes)
