from unittest.mock import patch

import pytest

from app.exceptions import OverfastError, ParserBlizzardError
from app.heroes.parsers.hero_stats_summary_parser import HeroStatsSummaryParser
from app.players.enums import (
    CompetitiveDivision,
    PlayerGamemode,
    PlayerPlatform,
    PlayerRegion,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("parser_init_kwargs", "blizzard_query_params", "raises_error"),
    [
        # Nominal case
        (
            {},
            {},
            False,
        ),
        # Specific filter (tier)
        (
            {"competitive_division": CompetitiveDivision.DIAMOND},
            {"tier": "Diamond"},
            False,
        ),
        # Invalid map filter (not compatible with competitive)
        (
            {"map": "hanaoka"},
            {"map": "hanaoka"},
            True,
        ),
    ],
)
async def test_hero_stats_summary_parser(
    parser_init_kwargs: dict,
    blizzard_query_params: dict,
    raises_error: bool,
    hero_stats_response_mock: str,
):
    base_kwargs = {
        "platform": PlayerPlatform.PC,
        "gamemode": PlayerGamemode.COMPETITIVE,
        "region": PlayerRegion.EUROPE,
        "order_by": "hero:asc",
    }
    init_kwargs = base_kwargs | parser_init_kwargs

    # Instanciate with given kwargs
    parser = HeroStatsSummaryParser(**init_kwargs)

    # Ensure running the parsing won't fail
    with patch("httpx.AsyncClient.get", return_value=hero_stats_response_mock):
        if raises_error:
            with pytest.raises(
                ParserBlizzardError,
                match=(
                    f"Selected map '{init_kwargs['map']}' is not compatible "
                    f"with '{init_kwargs['gamemode']}' gamemode"
                ),
            ):
                await parser.parse()
        else:
            try:
                await parser.parse()
            except OverfastError:
                pytest.fail("Hero stats summary parsing failed")

    # Ensure we're sending the right parameters to Blibli
    base_query_params = {
        "input": "PC",
        "rq": "1",
        "region": "Europe",
        "map": "all-maps",
        "tier": "All",
    }
    query_params = base_query_params | blizzard_query_params
    assert parser.get_blizzard_query_params(**init_kwargs) == query_params
