from unittest.mock import Mock, patch

import pytest

from app.adapters.blizzard.parsers.hero_stats_summary import parse_hero_stats_summary
from app.exceptions import ParserBlizzardError
from app.overfast_client import OverFastClient
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
