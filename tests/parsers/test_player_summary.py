"""Tests for parse_player_summary_json"""

import pytest

from app.adapters.blizzard.parsers.player_summary import parse_player_summary_json
from app.exceptions import ParserParsingError

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
