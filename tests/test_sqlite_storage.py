"""Tests for SQLiteStorage adapter"""

import json

import pytest


class TestStaticData:
    """Test static data storage operations"""

    @pytest.mark.asyncio
    async def test_set_and_get_static_data(self, storage_db):
        """Test round-trip for static data with compression"""
        test_data = {
            "key": "hero-ana",
            "name": "Ana",
            "role": "support",
            "abilities": ["Sleep Dart", "Biotic Grenade"],
        }

        # Store data
        await storage_db.set_static_data(
            key="hero-ana",
            data=json.dumps(test_data),
            data_type="heroes",
            schema_version=1,
        )

        # Retrieve data
        result = await storage_db.get_static_data("hero-ana")

        # Verify
        assert result is not None
        assert result["data_type"] == "heroes"
        assert result["schema_version"] == 1
        assert json.loads(result["data"]) == test_data
        assert result["updated_at"] > 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_static_data(self, storage_db):
        """Test getting non-existent static data returns None"""
        result = await storage_db.get_static_data("nonexistent-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_static_data(self, storage_db):
        """Test updating existing static data"""
        # Insert initial data
        await storage_db.set_static_data(
            key="hero-mercy",
            data=json.dumps({"version": 1}),
            data_type="heroes",
            schema_version=1,
        )

        first_result = await storage_db.get_static_data("hero-mercy")
        first_timestamp = first_result["updated_at"]

        # Update data
        new_schema_version = 2
        await storage_db.set_static_data(
            key="hero-mercy",
            data=json.dumps({"version": new_schema_version}),
            data_type="heroes",
            schema_version=new_schema_version,
        )

        # Verify update
        updated_result = await storage_db.get_static_data("hero-mercy")
        assert json.loads(updated_result["data"])["version"] == new_schema_version
        assert updated_result["schema_version"] == new_schema_version
        assert updated_result["updated_at"] >= first_timestamp


class TestPlayerProfiles:
    """Test player profile storage operations"""

    @pytest.mark.asyncio
    async def test_set_and_get_player_profile_with_summary(self, storage_db):
        """Test storing and retrieving player profile with full summary"""
        player_id = "TeKrop-2217"
        html = "<html>Player profile data</html>"
        summary = {
            "name": "TeKrop",
            "avatar": "https://example.com/avatar.jpg",
            "namecard": "https://example.com/namecard.jpg",
            "title": {"en_US": "Harbinger"},
            "isPublic": True,
            "lastUpdated": 1678536999,
            "url": "c65b8798bc61d6ffbba120|...",
        }

        # Store profile
        await storage_db.set_player_profile(
            player_id=player_id,
            html=html,
            summary=summary,
        )

        # Retrieve profile
        result = await storage_db.get_player_profile(player_id)

        # Verify
        assert result is not None
        # Player ID not returned - we query by it == player_id
        assert result["html"] == html
        assert result["summary"] == summary
        assert result["updated_at"] > 0

    @pytest.mark.asyncio
    async def test_set_and_get_player_profile_without_summary(self, storage_db):
        """Test storing profile without summary (legacy compatibility)"""
        player_id = "Player-1234"
        html = "<html>Legacy profile</html>"

        # Store profile without summary
        await storage_db.set_player_profile(
            player_id=player_id,
            html=html,
            summary=None,
        )

        # Retrieve profile
        result = await storage_db.get_player_profile(player_id)

        # Verify - should have minimal summary
        assert result is not None
        # Player ID not returned - we query by it == player_id
        assert result["html"] == html
        assert "summary" in result
        # Minimal summary should have basic structure (but values may be None)
        assert "url" in result["summary"]
        assert "lastUpdated" in result["summary"]
        # Phase 3.5B: player_id IS the Blizzard ID, check summary has it
        assert result["summary"]["url"] == player_id
        assert result["last_updated_blizzard"] is None

    @pytest.mark.asyncio
    async def test_get_nonexistent_player_profile(self, storage_db):
        """Test getting non-existent player profile returns None"""
        result = await storage_db.get_player_profile("NonExistent-9999")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_player_profile(self, storage_db):
        """Test updating existing player profile"""
        player_id = "UpdateTest-1111"

        # Insert initial profile
        await storage_db.set_player_profile(
            player_id=player_id,
            html="<html>Version 1</html>",
            summary={"lastUpdated": 1000000},
        )

        first_result = await storage_db.get_player_profile(player_id)
        first_timestamp = first_result["updated_at"]

        # Update profile
        await storage_db.set_player_profile(
            player_id=player_id,
            html="<html>Version 2</html>",
            summary={"lastUpdated": 2000000},
        )

        # Verify update
        updated_result = await storage_db.get_player_profile(player_id)
        assert updated_result["html"] == "<html>Version 2</html>"
        assert updated_result["summary"]["lastUpdated"] == 2000000  # noqa: PLR2004
        assert updated_result["updated_at"] >= first_timestamp

    @pytest.mark.asyncio
    async def test_get_player_id_by_battletag(self, storage_db):
        """Test BattleTag lookup optimization (Phase 3.5B)"""
        player_id = "Player-1234"
        battletag = "TestPlayer-5678"
        html = "<html>Profile with BattleTag</html>"
        summary = {"url": player_id, "lastUpdated": 1234567890}

        # Store profile with BattleTag
        await storage_db.set_player_profile(
            player_id=player_id,
            html=html,
            summary=summary,
            battletag=battletag,
        )

        # Lookup by BattleTag should return Blizzard ID
        result = await storage_db.get_player_id_by_battletag(battletag)
        assert result == player_id

    @pytest.mark.asyncio
    async def test_get_player_id_by_battletag_not_found(self, storage_db):
        """Test BattleTag lookup returns None for unknown BattleTag"""
        result = await storage_db.get_player_id_by_battletag("Unknown-9999")
        assert result is None


class TestStorageStats:
    """Test storage statistics and metrics"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_counts_and_size(self, storage_db):
        """Test that get_stats returns row counts and estimated size"""
        # Seed some data
        await storage_db.set_static_data(
            key="map-ilios",
            data=json.dumps({"name": "Ilios"}),
            data_type="maps",
            schema_version=1,
        )
        await storage_db.set_player_profile(
            player_id="Stats-1234",
            html="<html>Profile</html>",
            summary={"name": "Stats"},
        )

        # Get stats
        stats = await storage_db.get_stats()

        # Verify structure
        assert "size_bytes" in stats
        assert "static_data_count" in stats
        assert "player_profiles_count" in stats

        # Verify counts
        assert stats["static_data_count"] == 1
        assert stats["player_profiles_count"] == 1

        # Size should be estimated for in-memory DB
        assert stats["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_get_stats_with_empty_database(self, storage_db):
        """Test get_stats with no data returns zeros"""
        stats = await storage_db.get_stats()

        assert stats["static_data_count"] == 0
        assert stats["player_profiles_count"] == 0
        # Size can be > 0 due to schema overhead
        assert stats["size_bytes"] >= 0


class TestCompressionIntegrity:
    """Test that zstd compression/decompression works correctly"""

    @pytest.mark.asyncio
    async def test_large_html_compression(self, storage_db):
        """Test storing and retrieving large HTML content"""
        player_id = "LargeHTML-5555"
        # Create a large HTML string (~10KB)
        large_html = "<html>" + ("x" * 10000) + "</html>"

        await storage_db.set_player_profile(
            player_id=player_id,
            html=large_html,
            summary={"name": "Large"},
        )

        result = await storage_db.get_player_profile(player_id)

        # Verify content integrity after compression/decompression
        assert result["html"] == large_html
        assert len(result["html"]) == len(large_html)

    @pytest.mark.asyncio
    async def test_unicode_data_compression(self, storage_db):
        """Test that unicode characters survive compression"""
        test_data = {
            "name": "Lúcio",
            "title": "DJ",
            "emoji": "🎵🎶",
            "description": "Héros de soutien avec des beats",
        }

        await storage_db.set_static_data(
            key="hero-lucio",
            data=json.dumps(test_data, ensure_ascii=False),
            data_type="heroes",
            schema_version=1,
        )

        result = await storage_db.get_static_data("hero-lucio")
        retrieved_data = json.loads(result["data"])

        # Verify unicode integrity
        assert retrieved_data["name"] == "Lúcio"
        assert retrieved_data["emoji"] == "🎵🎶"
        assert retrieved_data["description"] == "Héros de soutien avec des beats"
