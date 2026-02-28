from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard import OverFastClient
from app.adapters.blizzard.parsers.heroes import (
    fetch_heroes_html,
    filter_heroes,
    parse_heroes_html,
)
from app.domain.enums import HeroGamemode, HeroKey, Role


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
    assert filter_heroes(heroes, role=None, gamemode=None) == heroes


@pytest.mark.asyncio
async def test_fetch_heroes_html_calls_blizzard(heroes_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        client = OverFastClient()
        html = await fetch_heroes_html(client)

    assert html == heroes_html_data
