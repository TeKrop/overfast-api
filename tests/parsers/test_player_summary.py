"""Tests for parse_player_summary_json"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard import BlizzardClient
from app.domain.exceptions import ParserParsingError
from app.domain.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary,
    parse_player_summary_json,
)

# Shared fixtures
PLAYER_BLIZZARD_ID = "abc123%7Cdef456"
OTHER_BLIZZARD_ID = "xxx999%7Cyyy000"
THIRD_BLIZZARD_ID = "zzz111%7Cwww222"

SINGLE_PLAYER_BLIZZARD_URL = [
    {
        "name": "Progresso",
        "isPublic": True,
        "lastUpdated": 1700000000,
        "avatar": "https://example.com/avatar.png",
        "namecard": None,
        "title": None,
        "url": PLAYER_BLIZZARD_ID,
    }
]


class TestParsePlayerSummaryJsonDiscriminatorValidation:
    """Tests for the discriminator validation fix (issue #382).

    Without a Blizzard ID, we can never safely identify the player from search
    results: Blizzard always returns a Blizzard ID in the URL field, so the
    discriminator cannot be verified. A blizzard_id param is required to match.
    """

    def test_single_match_without_blizzard_id_returns_empty(self):
        """Single result with no blizzard_id param → empty dict.

        Without a Blizzard ID we cannot verify the player identity, regardless
        of how many name matches were found.
        """
        result = parse_player_summary_json(SINGLE_PLAYER_BLIZZARD_URL, "Progresso-2749")
        assert result == {}

    def test_single_match_no_discriminator_without_blizzard_id_returns_empty(self):
        """Single result, player_id without discriminator, no blizzard_id → empty dict."""
        json_data = [
            {
                "name": "Player",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            }
        ]
        result = parse_player_summary_json(json_data, "Player")
        assert result == {}

    def test_blizzard_id_url_with_matching_blizzard_id_returned(self):
        """Single result with Blizzard ID URL + matching blizzard_id param → returned."""
        result = parse_player_summary_json(
            SINGLE_PLAYER_BLIZZARD_URL, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID
        )
        assert result != {}
        assert result["url"] == PLAYER_BLIZZARD_ID

    def test_blizzard_id_url_with_wrong_blizzard_id_returns_empty(self):
        """Single result with Blizzard ID URL + non-matching blizzard_id → empty dict."""
        result = parse_player_summary_json(
            SINGLE_PLAYER_BLIZZARD_URL, "Progresso-2749", blizzard_id=OTHER_BLIZZARD_ID
        )
        assert result == {}

    def test_multiple_players_resolved_by_blizzard_id(self):
        """Multiple name matches with blizzard_id provided → correct one returned."""
        json_data = [
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000001,
                "avatar": "https://example.com/a1.png",
                "namecard": None,
                "title": None,
                "url": OTHER_BLIZZARD_ID,
            },
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/a2.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            },
        ]
        result = parse_player_summary_json(
            json_data, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID
        )
        assert result != {}
        assert result["url"] == PLAYER_BLIZZARD_ID

    def test_single_match_with_blizzard_id_verified(self):
        """Single result + blizzard_id verifies even when only one name match.

        Previously, a single name match skipped blizzard_id verification entirely.
        Now the blizzard_id is always checked when provided.
        """
        result = parse_player_summary_json(
            SINGLE_PLAYER_BLIZZARD_URL, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID
        )
        assert result != {}

    def test_no_matching_players_returns_empty(self):
        """No public player with matching name → empty dict."""
        json_data = [
            {
                "name": "SomebodyElse",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            }
        ]
        result = parse_player_summary_json(json_data, "Progresso-2749")
        assert result == {}

    def test_private_player_excluded(self):
        """Private player with matching name is excluded → empty dict."""
        json_data = [
            {
                "name": "Progresso",
                "isPublic": False,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            }
        ]
        result = parse_player_summary_json(json_data, "Progresso-2749")
        assert result == {}

    def test_multiple_players_non_matching_blizzard_id_returns_empty(self):
        """Multiple name matches with blizzard_id that matches none → empty dict."""
        json_data = [
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000001,
                "avatar": "https://example.com/a1.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            },
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/a2.png",
                "namecard": None,
                "title": None,
                "url": THIRD_BLIZZARD_ID,
            },
        ]
        result = parse_player_summary_json(
            json_data, "Progresso-2749", blizzard_id=OTHER_BLIZZARD_ID
        )
        assert result == {}

    def test_multiple_public_players_same_name_no_blizzard_id_returns_empty(self):
        """Multiple public players with same name and no blizzard_id → empty dict."""
        json_data = [
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/a1.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            },
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000001,
                "avatar": "https://example.com/a2.png",
                "namecard": None,
                "title": None,
                "url": OTHER_BLIZZARD_ID,
            },
        ]
        result = parse_player_summary_json(json_data, "Progresso")
        assert result == {}

    def test_no_name_match_with_blizzard_id_returns_empty(self):
        """No public player matches the name despite blizzard_id being provided → empty dict."""
        json_data = [
            {
                "name": "SomeoneElse",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            }
        ]
        result = parse_player_summary_json(
            json_data, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID
        )
        assert result == {}

    def test_invalid_payload_raises_parsing_error(self):
        """Malformed payload raises ParserParsingError."""
        with pytest.raises(ParserParsingError):
            parse_player_summary_json([{"bad": "data"}], "Progresso-2749")


class TestPortraitNormalization:
    """Tests for the portrait→avatar/namecard/title normalization branch (lines 102-105)."""

    def test_portrait_field_sets_avatar_namecard_title_to_none(self):
        """When a player has a 'portrait' field, avatar/namecard/title are forced to None."""

        # Arrange
        json_data = [
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "portrait": "https://example.com/portrait.png",
                "url": PLAYER_BLIZZARD_ID,
                "avatar": "https://example.com/avatar.png",
                "namecard": "https://example.com/namecard.png",
                "title": "Legend",
            }
        ]

        # Act
        result = parse_player_summary_json(
            json_data, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID
        )

        # Assert
        assert result != {}
        assert result["avatar"] is None
        assert result["namecard"] is None
        assert result["title"] is None
        # portrait field itself is still present
        assert result["portrait"] == "https://example.com/portrait.png"

    def test_no_portrait_field_preserves_avatar(self):
        """When there is no 'portrait' field, avatar is kept as-is."""
        json_data = [
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": PLAYER_BLIZZARD_ID,
            }
        ]
        result = parse_player_summary_json(
            json_data, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID
        )
        assert result != {}
        assert result["avatar"] == "https://example.com/avatar.png"


class TestFetchPlayerSummaryJson:
    """Tests for fetch_player_summary_json (line 34-37)."""

    @pytest.mark.asyncio
    async def test_fetch_calls_blizzard_and_returns_json(self):
        json_payload = [{"name": "TeKrop", "url": "abc123"}]
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            json=lambda: json_payload,
        )
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = BlizzardClient()
            result = await fetch_player_summary_json(client, "TeKrop-2217")
        assert result == json_payload


class TestParsePlayerSummaryHighLevel:
    """Tests for parse_player_summary() high-level async function (lines 134-141)."""

    @pytest.mark.asyncio
    async def test_blizzard_id_returns_empty_without_fetch(self):
        """parse_player_summary skips the search when given a Blizzard ID."""
        mock_client = AsyncMock()
        # If a Blizzard ID is passed, no HTTP call should be made
        result = await parse_player_summary(
            mock_client, "abc123%7Cdef456", blizzard_id=None
        )
        assert result == {}
        mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_battletag_triggers_fetch_and_parse(self):
        """parse_player_summary fetches and parses for a normal BattleTag."""
        json_payload = [
            {
                "name": "TeKrop",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": "abc123%7Cdef456",
            }
        ]
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            json=lambda: json_payload,
        )
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = BlizzardClient()
            result = await parse_player_summary(
                client, "TeKrop-2217", blizzard_id="abc123%7Cdef456"
            )
        assert result != {}
        assert result["url"] == "abc123%7Cdef456"
