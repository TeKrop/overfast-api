"""Tests for app/domain/parsers/player_search.py — error paths and edge cases"""

import pytest

from app.domain.exceptions import ParserParsingError
from app.domain.parsers.player_search import (
    apply_ordering,
    filter_players_by_name,
    transform_player_search_results,
)

# ── filter_players_by_name ────────────────────────────────────────────────────


class TestFilterPlayersByName:
    def test_returns_matching_public_players(self):
        players = [
            {"name": "Test", "isPublic": True},
            {"name": "Other", "isPublic": True},
            {"name": "Test", "isPublic": False},
        ]
        result = filter_players_by_name(players, "Test")

        assert len(result) == 1
        assert result[0]["name"] == "Test"
        assert result[0]["isPublic"] is True

    def test_empty_list_returns_empty(self):
        actual = filter_players_by_name([], "Test")

        assert actual == []

    def test_no_match_returns_empty(self):
        players = [{"name": "Other", "isPublic": True}]
        actual = filter_players_by_name(players, "Test")

        assert actual == []

    def test_key_error_raises_parser_parsing_error(self):
        """Malformed player dict (missing required key) raises ParserParsingError."""
        players = [{"wrong_key": "value"}]  # missing 'name' and 'isPublic'
        with pytest.raises(
            ParserParsingError, match="Unexpected Blizzard search payload"
        ):
            filter_players_by_name(players, "Test")

    def test_none_in_list_raises_parser_parsing_error(self):
        """None item in list (TypeError) raises ParserParsingError."""
        with pytest.raises(ParserParsingError):
            filter_players_by_name([None], "Test")  # type: ignore[list-item]

    def test_uses_base_name_before_discriminator(self):
        """Name with discriminator: only the part before '-' is matched."""
        players = [{"name": "Player", "isPublic": True}]
        result = filter_players_by_name(players, "Player-1234")

        assert len(result) == 1


# ── transform_player_search_results ──────────────────────────────────────────


def _make_player(**overrides) -> dict:
    base = {
        "name": "Test",
        "url": "Test-1234",
        "avatar": "https://example.com/avatar.png",
        "namecard": None,
        "title": None,
        "lastUpdated": 1700000000,
        "isPublic": True,
        "portrait": None,
    }
    base.update(overrides)
    return base


class TestTransformPlayerSearchResults:
    def test_basic_transform(self):
        player = _make_player()
        result = transform_player_search_results([player], "Test")

        assert len(result) == 1
        r = result[0]

        assert r["player_id"] == "Test-1234"
        assert r["name"] == "Test"

    def test_portrait_branch_nullifies_avatar_namecard_title(self):
        """When portrait is present, avatar/namecard/title are set to None."""
        player = _make_player(
            portrait="https://example.com/portrait.png",
            avatar="https://example.com/avatar.png",
            namecard="https://example.com/namecard.png",
            title="Philosopher",
        )
        result = transform_player_search_results([player], "Test")
        r = result[0]

        assert r["avatar"] is None
        assert r["namecard"] is None
        assert r["title"] is None

    def test_single_result_with_discriminator_uses_search_nickname(self):
        """Single result + discriminator in search → player_id = search_nickname."""
        player = _make_player(url="Test-9999")
        result = transform_player_search_results([player], "Test-9999")

        assert result[0]["player_id"] == "Test-9999"

    def test_multiple_results_use_url_as_player_id(self):
        """Multiple results → player_id = player['url'] regardless of search."""
        p1 = _make_player(name="Test", url="Test-0001")
        p2 = _make_player(name="Test", url="Test-0002")
        results = transform_player_search_results([p1, p2], "Test-0001")

        assert results[0]["player_id"] == "Test-0001"
        assert results[1]["player_id"] == "Test-0002"

    def test_missing_required_field_raises_parser_parsing_error(self):
        """Missing 'url' key raises ParserParsingError."""
        player = {"name": "Test"}  # missing required fields
        with pytest.raises(ParserParsingError, match="Missing required field"):
            transform_player_search_results([player], "Test")


# ── apply_ordering ────────────────────────────────────────────────────────────


class TestApplyOrdering:
    def test_sorts_ascending(self):
        players = [{"name": "Beta"}, {"name": "Alpha"}]
        result = apply_ordering(players, "name:asc")

        assert [p["name"] for p in result] == ["Alpha", "Beta"]

    def test_sorts_descending(self):
        players = [{"name": "Alpha"}, {"name": "Beta"}]
        result = apply_ordering(players, "name:desc")

        assert [p["name"] for p in result] == ["Beta", "Alpha"]

    def test_invalid_format_raises_parser_parsing_error(self):
        """Missing ':' in order_by raises ParserParsingError."""
        with pytest.raises(ParserParsingError, match="Invalid ordering"):
            apply_ordering([{"name": "X"}], "name_asc")

    def test_invalid_field_raises_parser_parsing_error(self):
        """Non-existent sort field raises ParserParsingError."""
        players = [{"name": "X"}]
        with pytest.raises(ParserParsingError, match="Invalid ordering"):
            apply_ordering(players, "nonexistent_field:asc")
