from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.enums import Locale, PlayerGamemode, PlayerPlatform, PlayerRegion
from app.domain.exceptions import (
    InvalidGamemodeFilterError,
    ParserInternalError,
    ParserParsingError,
)
from app.domain.services.hero_service import HeroService, dict_insert_value_before_key


def _make_hero_service() -> HeroService:
    cache = AsyncMock()
    storage = AsyncMock()
    blizzard_client = AsyncMock()
    task_queue = AsyncMock()
    task_queue.is_job_pending_or_running.return_value = False
    return HeroService(cache, storage, blizzard_client, task_queue)


class TestHeroServiceListHeroesParseError:
    def test_parse_raises_parser_internal_error_on_parser_parsing_error(self):
        svc = _make_hero_service()
        config = svc._heroes_list_config(Locale.ENGLISH_US, "/heroes")
        parser = config.parser
        assert parser is not None

        with (
            patch(
                "app.domain.services.hero_service.parse_heroes_html",
                side_effect=ParserParsingError("bad HTML"),
            ),
            pytest.raises(ParserInternalError) as exc_info,
        ):
            parser("<bad-html>")

        assert str(Locale.ENGLISH_US) in exc_info.value.blizzard_url


class TestHeroServiceGetHeroStatsParseError:
    @pytest.mark.asyncio
    async def test_get_hero_stats_raises_parser_internal_error_on_parser_parsing_error(
        self,
    ):
        svc = _make_hero_service()

        with (
            patch(
                "app.domain.services.hero_service.parse_hero_stats_summary",
                side_effect=ParserParsingError("unexpected JSON"),
            ),
            pytest.raises(ParserInternalError),
        ):
            await svc.get_hero_stats(
                platform=PlayerPlatform.PC,
                gamemode=PlayerGamemode.QUICKPLAY,
                region=PlayerRegion.EUROPE,
                role=None,
                map_filter=None,
                competitive_division=None,
                order_by="hero:asc",
                cache_key="/heroes/stats",
            )


class TestHeroServiceGetHeroStatsGamemodeFilter:
    _base_kwargs: ClassVar[dict] = {
        "platform": PlayerPlatform.PC,
        "gamemode": PlayerGamemode.COMPETITIVE,
        "region": PlayerRegion.EUROPE,
        "role": None,
        "map_filter": None,
        "competitive_division": None,
        "order_by": "hero:asc",
        "cache_key": "/heroes/stats",
    }

    @pytest.mark.asyncio
    async def test_retries_on_invalid_gamemode_filter(self):
        svc = _make_hero_service()
        expected = [{"hero": "ana", "pickrate": 0.1, "winrate": 0.5}]

        with patch(
            "app.domain.services.hero_service.parse_hero_stats_summary",
            side_effect=[
                InvalidGamemodeFilterError("filter '1' != selected '2'"),
                expected,
            ],
        ) as mock_parse:
            data, _, _ = await svc.get_hero_stats(**self._base_kwargs)

        assert data == expected
        assert mock_parse.call_count == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_raises_parser_internal_error_when_all_filters_exhausted(self):
        svc = _make_hero_service()

        with (
            patch(
                "app.domain.services.hero_service.parse_hero_stats_summary",
                side_effect=InvalidGamemodeFilterError("no valid filter found"),
            ),
            pytest.raises(ParserInternalError),
        ):
            await svc.get_hero_stats(**self._base_kwargs)

    @pytest.mark.asyncio
    async def test_returns_empty_list_without_retry(self):
        svc = _make_hero_service()

        with patch(
            "app.domain.services.hero_service.parse_hero_stats_summary",
            return_value=[],
        ) as mock_parse:
            data, _, _ = await svc.get_hero_stats(**self._base_kwargs)

        assert data == []
        assert mock_parse.call_count == 1


@pytest.mark.parametrize(
    ("input_dict", "key", "new_key", "new_value"),
    [
        # Empty dict
        ({}, "key", "new_key", "new_value"),
        # Key doesn't exist
        ({"key_one": 1, "key_two": 2}, "key", "new_key", "new_value"),
    ],
)
def test_dict_insert_value_before_key_with_key_error(
    input_dict: dict,
    key: str,
    new_key: str,
    new_value: Any,
):
    with pytest.raises(KeyError):
        dict_insert_value_before_key(input_dict, key, new_key, new_value)


@pytest.mark.parametrize(
    ("input_dict", "key", "new_key", "new_value", "result_dict"),
    [
        # Before first key
        (
            {"key_one": 1, "key_two": 2, "key_three": 3},
            "key_one",
            "key_four",
            4,
            {"key_four": 4, "key_one": 1, "key_two": 2, "key_three": 3},
        ),
        # Before middle key
        (
            {"key_one": 1, "key_two": 2, "key_three": 3},
            "key_two",
            "key_four",
            4,
            {"key_one": 1, "key_four": 4, "key_two": 2, "key_three": 3},
        ),
        # Before last key
        (
            {"key_one": 1, "key_two": 2, "key_three": 3},
            "key_three",
            "key_four",
            4,
            {"key_one": 1, "key_two": 2, "key_four": 4, "key_three": 3},
        ),
    ],
)
def test_dict_insert_value_before_key_valid(
    input_dict: dict,
    key: str,
    new_key: str,
    new_value: Any,
    result_dict: dict,
):
    actual = dict_insert_value_before_key(input_dict, key, new_key, new_value)

    assert actual == result_dict
