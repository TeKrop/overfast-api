"""Tests for Blizzard parser utility functions"""

from app.adapters.blizzard.parsers.utils import (
    extract_blizzard_id_from_url,
    is_blizzard_id,
    match_player_by_blizzard_id,
)


class TestIsBlizzardId:
    """Test is_blizzard_id function"""

    def test_battletag_format(self):
        """Should return False for BattleTag format (Name-12345)"""
        assert is_blizzard_id("TeKrop-2217") is False
        assert is_blizzard_id("Player-1234") is False
        assert is_blizzard_id("Kindness-11556") is False

    def test_blizzard_id_url_encoded(self):
        """Should return True for Blizzard ID with URL-encoded pipe (%7C)"""
        assert (
            is_blizzard_id("df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f")
            is True
        )
        assert is_blizzard_id("abc123%7Cdef456") is True

    def test_blizzard_id_pipe(self):
        """Should return True for Blizzard ID with pipe (|)"""
        assert (
            is_blizzard_id("df51a381fe20caf8baa7|0bf3b4c47cbebe84b8db9c676a4e9c1f")
            is True
        )
        assert is_blizzard_id("abc123|def456") is True

    def test_ambiguous_with_hyphen_and_pipe(self):
        """Should handle edge case with both hyphen and pipe (prioritize pipe)"""
        # This shouldn't happen in practice, but if it does, pipe indicates Blizzard ID
        assert is_blizzard_id("some-name|id") is False  # Has hyphen, fails check
        assert is_blizzard_id("somename|id") is True  # No hyphen, passes


class TestExtractBlizzardIdFromUrl:
    """Test extract_blizzard_id_from_url function"""

    def test_extract_from_full_url(self):
        """Should extract Blizzard ID from full URL (keeps URL-encoded format)"""
        url = "https://overwatch.blizzard.com/en-us/career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f/"
        expected = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        assert extract_blizzard_id_from_url(url) == expected

    def test_extract_from_path_only(self):
        """Should extract Blizzard ID from path (keeps URL-encoded format)"""
        url = "/career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f/"
        expected = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        assert extract_blizzard_id_from_url(url) == expected

    def test_extract_without_trailing_slash(self):
        """Should extract Blizzard ID without trailing slash"""
        url = "/career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        expected = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        assert extract_blizzard_id_from_url(url) == expected

    def test_extract_from_battle_tag_url(self):
        """Should extract Blizzard ID from BattleTag URL (after redirect)"""
        # This simulates what we get after Blizzard redirects BattleTag → ID
        url = "/en-us/career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f/"
        expected = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        assert extract_blizzard_id_from_url(url) == expected

    def test_keeps_url_encoding(self):
        """Should keep URL-encoded format (%7C, not |) to match search results"""
        url = "/career/abc123%7Cdef456/"
        expected = "abc123%7Cdef456"
        assert extract_blizzard_id_from_url(url) == expected

    def test_complex_blizzard_id(self):
        """Should handle complex Blizzard ID formats"""
        url = "/career/a1b2c3d4e5f6%7Cg7h8i9j0k1l2m3n4o5p6/"
        expected = "a1b2c3d4e5f6%7Cg7h8i9j0k1l2m3n4o5p6"
        assert extract_blizzard_id_from_url(url) == expected

    def test_no_career_path(self):
        """Should return None if /career/ not in URL"""
        url = "https://overwatch.blizzard.com/en-us/"
        assert extract_blizzard_id_from_url(url) is None

    def test_empty_url(self):
        """Should return None for empty URL"""
        assert extract_blizzard_id_from_url("") is None

    def test_malformed_url(self):
        """Should return None for malformed URL"""
        url = "/career/"
        assert extract_blizzard_id_from_url(url) is None

    def test_multiple_slashes(self):
        """Should handle URLs with additional path segments"""
        url = "/en-us/career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f/summary/"
        expected = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        assert extract_blizzard_id_from_url(url) == expected


class TestMatchPlayerByBlizzardId:
    """Test match_player_by_blizzard_id function"""

    def test_match_single_player(self):
        """Should match player by Blizzard ID (URL-encoded format)"""
        search_results = [
            {
                "name": "Kindness",
                "url": "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f",
                "isPublic": True,
            }
        ]
        blizzard_id = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        result = match_player_by_blizzard_id(search_results, blizzard_id)
        assert result is not None
        assert result["name"] == "Kindness"
        assert result["url"] == blizzard_id

    def test_match_among_multiple_players(self):
        """Should match correct player among multiple results"""
        search_results = [
            {"name": "Player", "url": "abc123%7Cdef456", "isPublic": True},
            {"name": "Player", "url": "ghi789%7Cjkl012", "isPublic": True},
            {
                "name": "Player",
                "url": "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f",
                "isPublic": True,
            },
            {"name": "Player", "url": "mno345%7Cpqr678", "isPublic": True},
        ]
        blizzard_id = "df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f"
        result = match_player_by_blizzard_id(search_results, blizzard_id)
        assert result is not None
        assert result["url"] == blizzard_id

    def test_no_match(self):
        """Should return None when Blizzard ID not found"""
        search_results = [
            {"name": "Player", "url": "abc123%7Cdef456", "isPublic": True},
            {"name": "Player", "url": "ghi789%7Cjkl012", "isPublic": True},
        ]
        blizzard_id = "notfound%7Cxyz999"
        result = match_player_by_blizzard_id(search_results, blizzard_id)
        assert result is None

    def test_empty_search_results(self):
        """Should return None for empty search results"""
        search_results = []
        blizzard_id = "abc123%7Cdef456"
        result = match_player_by_blizzard_id(search_results, blizzard_id)
        assert result is None

    def test_missing_url_field(self):
        """Should handle search results with missing 'url' field"""
        search_results = [
            {"name": "Player", "isPublic": True},  # Missing 'url'
            {"name": "Player", "url": "abc123%7Cdef456", "isPublic": True},
        ]
        blizzard_id = "abc123%7Cdef456"
        result = match_player_by_blizzard_id(search_results, blizzard_id)
        assert result is not None
        assert result["url"] == blizzard_id

    def test_returns_first_match(self):
        """Should return first matching player if multiple have same ID (edge case)"""
        # This shouldn't happen in practice, but test the behavior
        search_results = [
            {
                "name": "Player1",
                "url": "abc123%7Cdef456",
                "isPublic": True,
                "avatar": "url1",
            },
            {
                "name": "Player2",
                "url": "abc123%7Cdef456",
                "isPublic": True,
                "avatar": "url2",
            },
        ]
        blizzard_id = "abc123%7Cdef456"
        result = match_player_by_blizzard_id(search_results, blizzard_id)
        assert result is not None
        assert result["name"] == "Player1"  # First match
        assert result["avatar"] == "url1"
