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

SINGLE_PLAYER_BATTLETAG_URL = [
    {
        "name": "Progresso",
        "isPublic": True,
        "lastUpdated": 1700000000,
        "avatar": "https://example.com/avatar.png",
        "namecard": None,
        "title": None,
        "url": "Progresso-2749",
    }
]

WRONG_PLAYER_BATTLETAG_URL = [
    {
        "name": "Progresso",
        "isPublic": True,
        "lastUpdated": 1700000000,
        "avatar": "https://example.com/avatar.png",
        "namecard": None,
        "title": None,
        "url": "Progresso-1234",  # different discriminator
    }
]


class TestParsePlayerSummaryJsonDiscriminatorValidation:
    """Tests for the discriminator validation fix (issue #382).

    When a BattleTag like "Progresso-2749" is requested and search returns a
    different player with the same name, the wrong player must NOT be returned.
    """

    def test_correct_battletag_match_returned(self):
        """Single result whose BattleTag URL matches the request → returned."""
        result = parse_player_summary_json(SINGLE_PLAYER_BATTLETAG_URL, "Progresso-2749")
        assert result != {}
        assert result["url"] == "Progresso-2749"

    def test_wrong_battletag_returns_empty(self):
        """Single result whose BattleTag URL has a DIFFERENT discriminator → empty dict."""
        result = parse_player_summary_json(WRONG_PLAYER_BATTLETAG_URL, "Progresso-2749")
        assert result == {}

    def test_blizzard_id_url_without_blizzard_id_returns_empty(self):
        """Single result with Blizzard ID URL and no blizzard_id param → empty dict.

        We cannot verify whether this Blizzard ID corresponds to the requested
        discriminator, so we fall through to redirect-based resolution.
        """
        result = parse_player_summary_json(SINGLE_PLAYER_BLIZZARD_URL, "Progresso-2749")
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

    def test_battletag_url_with_wrong_blizzard_id_returns_empty(self):
        """Single result with BattleTag URL + non-matching blizzard_id → empty dict."""
        json_data = [
            {
                "name": "Progresso",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/a1.png",
                "namecard": None,
                "title": None,
                "url": "Progresso-2749",
            }
        ]
        result = parse_player_summary_json(
            json_data, "Progresso-2749", blizzard_id=OTHER_BLIZZARD_ID
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
        result = parse_player_summary_json(json_data, "Progresso-2749", blizzard_id=PLAYER_BLIZZARD_ID)
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

    def test_no_discriminator_single_match_accepted(self):
        """Player_id without discriminator and single match → accepted (no change)."""
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
        # "Player" has no "-" so discriminator validation is skipped
        result = parse_player_summary_json(json_data, "Player")
        assert result != {}

    def test_no_discriminator_single_battletag_url_accepted(self):
        """Player_id without discriminator, single BattleTag URL result → accepted."""
        json_data = [
            {
                "name": "Player",
                "isPublic": True,
                "lastUpdated": 1700000000,
                "avatar": "https://example.com/avatar.png",
                "namecard": None,
                "title": None,
                "url": "Player-1234",
            }
        ]
        # "Player" has no discriminator so validation is skipped entirely
        result = parse_player_summary_json(json_data, "Player")
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
                "url": "Progresso-2749",
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

    def test_invalid_payload_raises_parsing_error(self):
        """Malformed payload raises ParserParsingError."""
        with pytest.raises(ParserParsingError):
            parse_player_summary_json([{"bad": "data"}], "Progresso-2749")
