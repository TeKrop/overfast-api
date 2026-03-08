"""Unit tests for player_profile parser module"""

from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard import BlizzardClient
from app.domain.enums import PlayerGamemode, PlayerPlatform
from app.domain.exceptions import ParserBlizzardError
from app.domain.parsers.player_profile import (
    filter_all_stats_data,
    filter_stats_by_query,
    parse_player_profile,
    parse_player_profile_html,
)
from tests.helpers import read_html_file

_TEKROP_HTML = read_html_file("players/TeKrop-2217.html") or ""

# A stats structure mirroring parser output (string keys, not enum keys)
_PC_KEY = PlayerPlatform.PC.value
_CONSOLE_KEY = PlayerPlatform.CONSOLE.value
_QP_KEY = PlayerGamemode.QUICKPLAY.value
_COMP_KEY = PlayerGamemode.COMPETITIVE.value

_HERO_STATS = [
    {
        "category": "combat",
        "label": "Combat",
        "stats": [{"key": "eliminations", "label": "Eliminations", "value": 10}],
    }
]

_FULL_STATS = {
    _PC_KEY: {
        _QP_KEY: {
            "heroes_comparisons": {},
            "career_stats": {"tracer": _HERO_STATS, "genji": _HERO_STATS},
        },
        _COMP_KEY: None,
    },
    _CONSOLE_KEY: None,
}


# ---------------------------------------------------------------------------
# filter_stats_by_query
# ---------------------------------------------------------------------------


class TestFilterStatsByQuery:
    def test_no_platform_no_stats_returns_empty(self):
        """When all platform data is None, returns {}."""
        stats = {_PC_KEY: None, _CONSOLE_KEY: None}

        result = filter_stats_by_query(stats)

        assert result == {}

    def test_none_stats_returns_empty(self):
        """None input returns {}."""
        result = filter_stats_by_query(None)

        assert result == {}

    def test_auto_detect_platform(self):
        """Without explicit platform, first non-None platform is used."""
        # No gamemode specified → filtered_data after platform = {_QP_KEY: ..., _COMP_KEY: None}
        # Then gamemode_key=None → filtered_data.get(None) = {} → returns {}
        result = filter_stats_by_query(_FULL_STATS)

        # With no gamemode, get(None) returns {} → empty
        assert result == {}

    def test_explicit_platform_and_gamemode(self):
        """With explicit platform+gamemode, returns career_stats dict."""
        result = filter_stats_by_query(
            _FULL_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
        )

        assert "tracer" in result
        assert "genji" in result

    def test_hero_filter(self):
        """Hero filter restricts to specific hero."""
        result = filter_stats_by_query(
            _FULL_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
            hero="tracer",
        )

        assert result == {"tracer": _HERO_STATS}

    def test_hero_filter_no_match(self):
        """Hero filter with no match returns empty dict."""
        result = filter_stats_by_query(
            _FULL_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
            hero="mercy",
        )

        assert result == {}

    def test_platform_with_no_gamemode_data_returns_empty(self):
        """When gamemode data is None, returns {}."""
        stats = {
            _PC_KEY: {_QP_KEY: None, _COMP_KEY: None},
            _CONSOLE_KEY: None,
        }

        result = filter_stats_by_query(
            stats, platform=PlayerPlatform.PC, gamemode=PlayerGamemode.QUICKPLAY
        )

        assert result == {}

    def test_string_platform_and_gamemode(self):
        """String values for platform/gamemode are handled via str() fallback."""
        result = filter_stats_by_query(
            _FULL_STATS,
            platform=_PC_KEY,  # str, not enum
            gamemode=_QP_KEY,
        )

        assert "tracer" in result


# ---------------------------------------------------------------------------
# filter_all_stats_data
# ---------------------------------------------------------------------------


class TestFilterAllStatsData:
    def test_none_stats_returns_none(self):
        """None input → None."""
        result = filter_all_stats_data(None)

        assert result is None

    def test_empty_stats_returns_none(self):
        """Empty dict → None."""
        result = filter_all_stats_data({})

        assert result is None

    def test_all_none_values_returns_none(self):
        """Dict with all-None values → None."""
        result = filter_all_stats_data({_PC_KEY: None, _CONSOLE_KEY: None})

        assert result is None

    def test_no_filters_returns_both_platforms(self):
        """Without filters, returns both platform keys."""
        result = filter_all_stats_data(_FULL_STATS)

        assert result is not None
        assert _PC_KEY in result
        assert _CONSOLE_KEY in result

    def test_platform_filter_nulls_other_platform(self):
        """Platform filter sets non-matching platform to None."""
        result = filter_all_stats_data(_FULL_STATS, platform=PlayerPlatform.PC)

        assert result is not None
        assert result[_CONSOLE_KEY] is None
        assert result[_PC_KEY] is not None

    def test_platform_filter_console_nulls_pc(self):
        """Console filter sets PC to None."""
        result = filter_all_stats_data(_FULL_STATS, platform=PlayerPlatform.CONSOLE)

        assert result is not None
        assert result[_PC_KEY] is None
        assert result[_CONSOLE_KEY] is None  # no console data

    def test_gamemode_filter_nulls_other_gamemodes(self):
        """Gamemode filter keeps only matching gamemode per platform."""
        result = filter_all_stats_data(
            _FULL_STATS,
            gamemode=PlayerGamemode.QUICKPLAY,
        )

        assert result is not None
        pc_data = result[_PC_KEY]
        assert pc_data is not None
        assert pc_data[_QP_KEY] is not None
        assert pc_data[_COMP_KEY] is None

    def test_platform_and_gamemode_filter(self):
        """Both filters applied."""
        result = filter_all_stats_data(
            _FULL_STATS,
            platform=PlayerPlatform.PC,
            gamemode=PlayerGamemode.QUICKPLAY,
        )

        assert result is not None
        assert result[_CONSOLE_KEY] is None
        pc_data = result[_PC_KEY]
        assert pc_data is not None
        assert pc_data[_QP_KEY] is not None
        assert pc_data[_COMP_KEY] is None

    def test_string_filters(self):
        """String values for platform/gamemode are handled."""
        result = filter_all_stats_data(
            _FULL_STATS,
            platform=_PC_KEY,
            gamemode=_QP_KEY,
        )

        assert result is not None
        assert result[_PC_KEY] is not None

    def test_platform_data_is_none_stays_none(self):
        """If platform data is None in stats, stays None after filter."""
        result = filter_all_stats_data(_FULL_STATS, gamemode=PlayerGamemode.QUICKPLAY)

        assert result is not None
        assert result[_CONSOLE_KEY] is None


# ---------------------------------------------------------------------------
# parse_player_profile_html — edge cases
# ---------------------------------------------------------------------------


class TestParsePlayerProfileHtml:
    def test_real_fixture_returns_summary_and_stats(self):
        """Real HTML fixture produces valid summary+stats."""
        result = parse_player_profile_html(_TEKROP_HTML)

        assert "summary" in result
        assert "stats" in result

    def test_player_not_found_raises(self):
        """HTML without Profile-masthead raises ParserBlizzardError."""
        minimal_html = (
            "<html><body><main class='main-content'><div></div></main></body></html>"
        )

        with pytest.raises(ParserBlizzardError):
            parse_player_profile_html(minimal_html)

    def test_player_summary_overrides_avatar(self):
        """player_summary avatar overrides HTML avatar."""
        result = parse_player_profile_html(
            _TEKROP_HTML,
            player_summary={"avatar": "https://example.com/avatar.png"},
        )

        assert result["summary"]["avatar"] == "https://example.com/avatar.png"


# ---------------------------------------------------------------------------
# parse_player_profile — high-level async
# ---------------------------------------------------------------------------


class TestParsePlayerProfile:
    @pytest.mark.asyncio
    async def test_fetches_and_parses(self):
        """parse_player_profile fetches HTML and returns profile + blizzard_id."""
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            text=_TEKROP_HTML,
            url="https://overwatch.blizzard.com/career/abc123/",
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = BlizzardClient()
            result, _blizzard_id = await parse_player_profile(client, "TeKrop-2217")

        assert "summary" in result
        assert "stats" in result

    @pytest.mark.asyncio
    async def test_with_player_summary(self):
        """parse_player_profile passes player_summary through."""
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            text=_TEKROP_HTML,
            url="https://overwatch.blizzard.com/career/abc123/",
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = BlizzardClient()
            result, _ = await parse_player_profile(
                client,
                "TeKrop-2217",
                player_summary={"avatar": "https://example.com/custom.png"},
            )

        assert result["summary"]["avatar"] == "https://example.com/custom.png"
