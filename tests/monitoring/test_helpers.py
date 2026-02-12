"""Tests for monitoring helpers"""

from app.monitoring.helpers import normalize_blizzard_url, normalize_endpoint


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
        assert normalize_endpoint("/players/TeKrop-2217") == "/players/{player_id}"

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


class TestNormalizeBlizzardUrl:
    """Tests for normalize_blizzard_url function"""

    def test_career_url_with_battletag(self):
        """Career URL with BattleTag is normalized"""
        url = "https://overwatch.blizzard.com/en-us/career/TeKrop-2217/"
        assert normalize_blizzard_url(url) == "/career/{player_id}"

    def test_career_url_with_blizzard_id(self):
        """Career URL with Blizzard ID is normalized"""
        url = "https://overwatch.blizzard.com/en-us/career/df51a381fe20caf8baa7%7C0bf3b4c47cbebe84b8db9c676a4e9c1f/"
        assert normalize_blizzard_url(url) == "/career/{player_id}"

    def test_career_url_different_locales(self):
        """Career URLs with different locales are normalized identically"""
        urls = [
            "https://overwatch.blizzard.com/en-us/career/Player-1234/",
            "https://overwatch.blizzard.com/fr-fr/career/Player-1234/",
            "https://overwatch.blizzard.com/ko-kr/career/Player-1234/",
            "https://overwatch.blizzard.com/de-de/career/Player-1234/",
        ]
        expected = "/career/{player_id}"
        for url in urls:
            assert normalize_blizzard_url(url) == expected

    def test_career_url_without_trailing_slash(self):
        """Career URL without trailing slash is normalized"""
        url = "https://overwatch.blizzard.com/en-us/career/Player-1234"
        assert normalize_blizzard_url(url) == "/career/{player_id}"

    def test_hero_url_with_key(self):
        """Hero URL with hero key is normalized"""
        url = "https://overwatch.blizzard.com/en-us/heroes/ana/"
        assert normalize_blizzard_url(url) == "/heroes/{hero_key}"

    def test_hero_url_different_heroes(self):
        """Hero URLs for different heroes are normalized identically"""
        heroes = ["ana", "reinhardt", "mercy", "genji"]
        for hero in heroes:
            url = f"https://overwatch.blizzard.com/en-us/heroes/{hero}/"
            assert normalize_blizzard_url(url) == "/heroes/{hero_key}"

    def test_heroes_list_url(self):
        """Heroes list URL is preserved"""
        url = "https://overwatch.blizzard.com/en-us/heroes/"
        assert normalize_blizzard_url(url) == "/heroes"

    def test_heroes_list_url_without_trailing_slash(self):
        """Heroes list URL without trailing slash is preserved"""
        url = "https://overwatch.blizzard.com/en-us/heroes"
        assert normalize_blizzard_url(url) == "/heroes"

    def test_search_url_with_name(self):
        """Search URL with player name is normalized"""
        url = "https://overwatch.blizzard.com/en-us/search/account-by-name/TeKrop/"
        assert normalize_blizzard_url(url) == "/search/account-by-name/{search_name}"

    def test_search_url_different_names(self):
        """Search URLs with different names are normalized identically"""
        names = ["TeKrop", "Player", "Test-123", "User#1234"]
        for name in names:
            url = f"https://overwatch.blizzard.com/en-us/search/account-by-name/{name}/"
            assert (
                normalize_blizzard_url(url) == "/search/account-by-name/{search_name}"
            )

    def test_non_dynamic_path_locale_stripped(self):
        """Non-dynamic paths have locale stripped but path preserved"""
        url = "https://overwatch.blizzard.com/en-us/rates/data/"
        assert normalize_blizzard_url(url) == "/rates/data"

    def test_non_dynamic_path_different_locales(self):
        """Non-dynamic paths with different locales are normalized identically"""
        urls = [
            "https://overwatch.blizzard.com/en-us/rates/data/",
            "https://overwatch.blizzard.com/fr-fr/rates/data/",
            "https://overwatch.blizzard.com/ja-jp/rates/data/",
        ]
        expected = "/rates/data"
        for url in urls:
            assert normalize_blizzard_url(url) == expected

    def test_root_url(self):
        """Root URL with locale is normalized to /"""
        url = "https://overwatch.blizzard.com/en-us/"
        assert normalize_blizzard_url(url) == "/"

    def test_root_url_without_trailing_slash(self):
        """Root URL without trailing slash is normalized to /"""
        url = "https://overwatch.blizzard.com/en-us"
        assert normalize_blizzard_url(url) == "/"

    def test_url_with_query_parameters(self):
        """Query parameters are ignored in normalization"""
        url = "https://overwatch.blizzard.com/en-us/career/Player-1234/?param=value"
        assert normalize_blizzard_url(url) == "/career/{player_id}"

    def test_url_with_fragment(self):
        """URL fragments are ignored in normalization"""
        url = "https://overwatch.blizzard.com/en-us/heroes/ana/#abilities"
        assert normalize_blizzard_url(url) == "/heroes/{hero_key}"
