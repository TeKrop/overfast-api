"""Tests for monitoring helpers"""


from app.monitoring.helpers import normalize_endpoint


class TestNormalizeEndpoint:
    """Tests for normalize_endpoint function"""

    def test_normalize_player_summary(self):
        """Test normalization of player summary path"""
        assert (
            normalize_endpoint("/players/TeKrop-2217/summary")
            == "/players/{player_id}/summary"
        )

    def test_normalize_player_stats_career(self):
        """Test normalization of player stats career path"""
        assert (
            normalize_endpoint("/players/TeKrop-2217/stats/career")
            == "/players/{player_id}/stats/career"
        )

    def test_normalize_player_stats_summary(self):
        """Test normalization of player stats summary path"""
        assert (
            normalize_endpoint("/players/TeKrop-2217/stats/summary")
            == "/players/{player_id}/stats/summary"
        )

    def test_normalize_player_stats(self):
        """Test normalization of player stats path"""
        assert (
            normalize_endpoint("/players/TeKrop-2217/stats")
            == "/players/{player_id}/stats"
        )

    def test_normalize_player_career(self):
        """Test normalization of player career path"""
        assert (
            normalize_endpoint("/players/TeKrop-2217")
            == "/players/{player_id}"
        )

    def test_normalize_player_with_hash(self):
        """Test normalization of player ID with hash"""
        assert (
            normalize_endpoint("/players/username#1234/summary")
            == "/players/{player_id}/summary"
        )

    def test_normalize_player_blizzard_id(self):
        """Test normalization of numeric Blizzard ID"""
        assert (
            normalize_endpoint("/players/12345678/summary")
            == "/players/{player_id}/summary"
        )

    def test_normalize_player_blizzard_id_long(self):
        """Test normalization of long numeric Blizzard ID"""
        assert (
            normalize_endpoint("/players/1234567890123456/stats/career")
            == "/players/{player_id}/stats/career"
        )

    def test_normalize_player_blizzard_id_no_suffix(self):
        """Test normalization of Blizzard ID without path suffix"""
        assert normalize_endpoint("/players/12345678") == "/players/{player_id}"

    def test_normalize_hero_specific(self):
        """Test normalization of specific hero path"""
        assert normalize_endpoint("/heroes/ana") == "/heroes/{hero_key}"
        assert normalize_endpoint("/heroes/reinhardt") == "/heroes/{hero_key}"
        assert normalize_endpoint("/heroes/dva") == "/heroes/{hero_key}"

    def test_preserve_heroes_list(self):
        """Test that /heroes list endpoint is preserved"""
        assert normalize_endpoint("/heroes") == "/heroes"

    def test_preserve_heroes_stats(self):
        """Test that /heroes/stats endpoint is preserved"""
        assert normalize_endpoint("/heroes/stats") == "/heroes/stats"

    def test_preserve_players_search(self):
        """Test that /players search endpoint is preserved"""
        assert normalize_endpoint("/players") == "/players"

    def test_preserve_gamemodes(self):
        """Test that /gamemodes endpoint is preserved"""
        assert normalize_endpoint("/gamemodes") == "/gamemodes"

    def test_preserve_maps(self):
        """Test that /maps endpoint is preserved"""
        assert normalize_endpoint("/maps") == "/maps"

    def test_preserve_roles(self):
        """Test that /roles endpoint is preserved"""
        assert normalize_endpoint("/roles") == "/roles"

    def test_preserve_root(self):
        """Test that root endpoint is preserved"""
        assert normalize_endpoint("/") == "/"

    def test_preserve_static(self):
        """Test that static paths are preserved"""
        assert normalize_endpoint("/static/favicon.png") == "/static/favicon.png"
