from unittest.mock import Mock, patch

import pytest

from app.adapters.blizzard import OverFastClient
from app.adapters.blizzard.parsers.hero_stats_summary import (
    GAMEMODE_MAPPING,
    PLATFORM_MAPPING,
    parse_hero_stats_summary,
)
from app.exceptions import ParserBlizzardError
from app.players.enums import (
    CompetitiveDivision,
    PlayerGamemode,
    PlayerPlatform,
    PlayerRegion,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extra_kwargs", "raises_error"),
    [
        ({}, False),
        ({"competitive_division": CompetitiveDivision.DIAMOND}, False),
        ({"map_filter": "hanaoka"}, True),
    ],
)
async def test_parse_hero_stats_summary(
    extra_kwargs: dict,
    raises_error: bool,
    hero_stats_response_mock: Mock,
):
    base_kwargs = {
        "platform": PlayerPlatform.PC,
        "gamemode": PlayerGamemode.COMPETITIVE,
        "region": PlayerRegion.EUROPE,
        "order_by": "hero:asc",
    }

    with patch("httpx.AsyncClient.get", return_value=hero_stats_response_mock):
        client = OverFastClient()
        if raises_error:
            with pytest.raises(ParserBlizzardError):
                await parse_hero_stats_summary(client, **base_kwargs, **extra_kwargs)  # ty: ignore[invalid-argument-type]
        else:
            result = await parse_hero_stats_summary(
                client,
                **base_kwargs,  # ty: ignore[invalid-argument-type]
                **extra_kwargs,
            )
            assert isinstance(result, list)
            assert len(result) > 0
            assert "hero" in result[0]


@pytest.mark.asyncio
async def test_parse_hero_stats_summary_query_params(hero_stats_response_mock: Mock):
    """Verify the exact Blizzard query parameters built by the parser."""
    platform = PlayerPlatform.PC
    gamemode = PlayerGamemode.COMPETITIVE
    region = PlayerRegion.EUROPE
    division = CompetitiveDivision.DIAMOND
    map_key = "all-maps"

    with patch(
        "httpx.AsyncClient.get", return_value=hero_stats_response_mock
    ) as mock_get:
        client = OverFastClient()
        await parse_hero_stats_summary(
            client,
            platform=platform,
            gamemode=gamemode,
            region=region,
            competitive_division=division,
            map_filter=map_key,
            order_by="hero:asc",
        )

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    params = kwargs.get("params", {})

    assert params["input"] == PLATFORM_MAPPING[platform]
    assert params["rq"] == GAMEMODE_MAPPING[gamemode]
    assert params["region"] == region.capitalize()
    assert params["map"] == map_key
    assert params["tier"] == division.capitalize()


@pytest.mark.asyncio
async def test_parse_hero_stats_summary_invalid_map_error_message(
    hero_stats_response_mock: Mock,
):
    """ParserBlizzardError message should name the incompatible map."""
    with patch("httpx.AsyncClient.get", return_value=hero_stats_response_mock):
        client = OverFastClient()
        with pytest.raises(ParserBlizzardError) as exc_info:
            await parse_hero_stats_summary(
                client,
                platform=PlayerPlatform.PC,
                gamemode=PlayerGamemode.COMPETITIVE,
                region=PlayerRegion.EUROPE,
                map_filter="hanaoka",
            )

    assert "hanaoka" in exc_info.value.message
    assert "compatible" in exc_info.value.message.lower()
