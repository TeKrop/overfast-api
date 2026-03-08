"""Unit tests for player_career_stats parser module"""

from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard import BlizzardClient
from app.domain.enums import PlayerGamemode, PlayerPlatform
from app.domain.parsers.player_career_stats import (
    _process_career_stats,
    extract_career_stats_from_profile,
    parse_player_career_stats,
    parse_player_career_stats_from_html,
)
from tests.helpers import read_html_file

# Use a real HTML fixture directly (avoids indirect parametrize complexity)
_TEKROP_HTML = read_html_file("players/TeKrop-2217.html") or ""

# Minimal profile data with one platform/gamemode/hero
_MINIMAL_CAREER_STATS = [
    {
        "category": "combat",
        "label": "Combat",
        "stats": [
            {"key": "eliminations", "label": "Eliminations", "value": 10},
        ],
    }
]

_PROFILE_WITH_STATS = {
    "summary": {"username": "TeKrop"},
    "stats": {
        PlayerPlatform.PC.value: {
            PlayerGamemode.QUICKPLAY.value: {
                "heroes_comparisons": {},
                "career_stats": {"tracer": _MINIMAL_CAREER_STATS},
            },
            PlayerGamemode.COMPETITIVE.value: None,
        },
        PlayerPlatform.CONSOLE.value: None,
    },
}

_PROFILE_NO_STATS = {
    "summary": {"username": "TeKrop"},
    "stats": None,
}


class TestExtractCareerStatsFromProfile:
    def test_empty_profile_returns_empty_dict(self):
        """Empty/None profile returns {}."""
        result_empty = extract_career_stats_from_profile({})
        result_no_stats = extract_career_stats_from_profile({"summary": {}})

        assert result_empty == {}
        assert result_no_stats == {}

    def test_none_stats_returns_empty_dict(self):
        """Profile with stats=None returns {}."""
        result = extract_career_stats_from_profile(_PROFILE_NO_STATS)

        assert result == {}

    def test_valid_profile_returns_nested_structure(self):
        """Profile with stats returns nested career_stats structure."""
        result = extract_career_stats_from_profile(_PROFILE_WITH_STATS)

        assert "stats" in result
        pc_stats = result["stats"].get(PlayerPlatform.PC.value)
        assert pc_stats is not None
        qp = pc_stats.get(PlayerGamemode.QUICKPLAY.value)
        assert qp is not None
        assert "career_stats" in qp
        assert "tracer" in qp["career_stats"]

    def test_hero_with_no_statistics_returns_none(self):
        """A hero with empty/None career stats maps to None."""
        profile = {
            "stats": {
                PlayerPlatform.PC.value: {
                    PlayerGamemode.QUICKPLAY.value: {
                        "heroes_comparisons": {},
                        "career_stats": {"tracer": None},
                    }
                },
                PlayerPlatform.CONSOLE.value: None,
            }
        }

        result = extract_career_stats_from_profile(profile)

        qp = result["stats"][PlayerPlatform.PC.value][PlayerGamemode.QUICKPLAY.value]
        assert qp["career_stats"]["tracer"] is None


class TestProcessCareerStats:
    def test_empty_profile_returns_empty(self):
        """_process_career_stats with empty profile returns {}."""
        result = _process_career_stats({})

        assert result == {}

    def test_no_filters_returns_full_structure(self):
        """Without filters, returns the full career_stats_data."""
        result = _process_career_stats(_PROFILE_WITH_STATS)

        assert "stats" in result

    def test_platform_filter_applied(self):
        """With platform filter, delegates to filter_stats_by_query."""
        result = _process_career_stats(
            _PROFILE_WITH_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
        )

        # With both platform and gamemode, returns per-hero dict
        assert isinstance(result, dict)

    def test_hero_filter_applied(self):
        """With hero filter, returns only that hero's stats."""
        result = _process_career_stats(
            _PROFILE_WITH_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
            hero="tracer",
        )

        assert "tracer" in result
        assert len(result) == 1

    def test_hero_filter_no_match_returns_empty(self):
        """Hero filter with no matching hero returns {}."""
        result = _process_career_stats(
            _PROFILE_WITH_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
            hero="genji",
        )

        assert result == {}


class TestParsePlayerCareerStatsFromHtml:
    def test_with_real_fixture_no_filter(self):
        """parse_player_career_stats_from_html returns a dict from real HTML."""
        result = parse_player_career_stats_from_html(_TEKROP_HTML)

        assert isinstance(result, dict)

    def test_with_platform_gamemode_filter(self):
        """Filters are applied correctly."""
        result = parse_player_career_stats_from_html(
            _TEKROP_HTML,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
        )

        assert isinstance(result, dict)


class TestParsePlayerCareerStatsAsync:
    @pytest.mark.asyncio
    async def test_calls_parse_player_profile_and_processes(self):
        """parse_player_career_stats fetches and processes career stats."""
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            text=_TEKROP_HTML,
            url="https://overwatch.blizzard.com/career/TeKrop-2217/",
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = BlizzardClient()
            result, _blizzard_id = await parse_player_career_stats(
                client,
                "TeKrop-2217",
            )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_with_filters(self):
        """parse_player_career_stats with platform/gamemode filters."""
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            text=_TEKROP_HTML,
            url="https://overwatch.blizzard.com/career/TeKrop-2217/",
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = BlizzardClient()
            result, _blizzard_id = await parse_player_career_stats(
                client,
                "TeKrop-2217",
                platform=PlayerPlatform.PC,
                gamemode=PlayerGamemode.QUICKPLAY,
            )

        assert isinstance(result, dict)
