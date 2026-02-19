import asyncio
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from valkey.exceptions import ValkeyError

from app.cache_manager import CacheManager
from app.config import settings
from app.enums import Locale

if TYPE_CHECKING:
    from fastapi import Request


@pytest.fixture
def cache_manager():
    return CacheManager()


@pytest.fixture
def locale():
    return Locale.ENGLISH_US


@pytest.mark.parametrize(
    ("req", "expected"),
    [
        (Mock(url=Mock(path="/heroes"), query_params=None), "/heroes"),
        (
            Mock(url=Mock(path="/heroes"), query_params="role=damage"),
            "/heroes?role=damage",
        ),
        (
            Mock(url=Mock(path="/players"), query_params="name=TeKrop"),
            "/players?name=TeKrop",
        ),
    ],
)
def test_get_cache_key_from_request(
    cache_manager: CacheManager,
    req: Request,
    expected: str,
):
    assert cache_manager.get_cache_key_from_request(req) == expected


@pytest.mark.parametrize(
    ("cache_key", "value", "expire", "sleep_time", "expected"),
    [
        ("/heroes", [{"name": "Sojourn"}], 10, 0, [{"name": "Sojourn"}]),
        ("/heroes", [{"name": "Sojourn"}], 1, 1, None),
    ],
)
@pytest.mark.asyncio
async def test_update_and_get_api_cache(
    cache_manager: CacheManager,
    cache_key: str,
    value: list,
    expire: int,
    sleep_time: int,
    expected: str | None,
):
    # Assert the value is not here before update
    assert await cache_manager.get_api_cache(cache_key) is None

    # Update the API Cache and sleep if needed
    await cache_manager.update_api_cache(cache_key, value, expire)
    await asyncio.sleep(sleep_time + 1)

    # Assert the value matches
    assert await cache_manager.get_api_cache(cache_key) == expected
    assert await cache_manager.get_api_cache("another_cache_key") is None


@pytest.mark.asyncio
async def test_valkey_connection_error(cache_manager: CacheManager, locale):
    """Test that cache operations handle Valkey connection errors gracefully"""
    valkey_connection_error = ValkeyError(
        "Error 111 connecting to 127.0.0.1:6379. Connection refused.",
    )
    heroes_cache_key = (
        f"HeroesParser-{settings.blizzard_host}/{locale}{settings.heroes_path}"
    )

    # Patch the async valkey server methods to raise errors
    with (
        patch.object(
            cache_manager.valkey_server,
            "set",
            side_effect=valkey_connection_error,
        ),
        patch.object(
            cache_manager.valkey_server,
            "get",
            side_effect=valkey_connection_error,
        ),
    ):
        # update_api_cache should handle error gracefully (log warning but not raise)
        await cache_manager.update_api_cache(
            heroes_cache_key,
            [{"name": "Sojourn"}],
            settings.heroes_path_cache_timeout,
        )

        # get_api_cache should return None on error
        result = await cache_manager.get_api_cache(heroes_cache_key)
        assert result is None


class TestPlayerStatus:
    """Tests for Valkey-based unknown player two-key pattern"""

    @pytest.mark.asyncio
    async def test_set_and_get_player_status_in_cooldown(self, cache_manager: CacheManager):
        """Cooldown key is set with TTL; get returns remaining retry_after and check_count"""
        blizzard_id = "abc123"
        check_count = 2
        retry_after = 1800

        await cache_manager.set_player_status(blizzard_id, check_count, retry_after)

        result = await cache_manager.get_player_status(blizzard_id)
        assert result is not None
        assert result["check_count"] == check_count
        assert 0 < result["retry_after"] <= retry_after

    @pytest.mark.asyncio
    async def test_get_player_status_with_battletag_early_rejection(
        self, cache_manager: CacheManager
    ):
        """Battletag-based cooldown key enables early rejection before identity resolution"""
        blizzard_id = "abc123"
        battletag = "TeKrop-2217"
        check_count = 1
        retry_after = 600

        await cache_manager.set_player_status(
            blizzard_id, check_count, retry_after, battletag=battletag
        )

        # Early rejection: lookup by battletag (before blizzard_id is resolved)
        result = await cache_manager.get_player_status(battletag)
        assert result is not None
        assert result["check_count"] == check_count

    @pytest.mark.asyncio
    async def test_get_player_status_persists_after_cooldown_expiry(
        self, cache_manager: CacheManager
    ):
        """Status key (no TTL) remains accessible after cooldown TTL expires"""
        blizzard_id = "persistent123"
        check_count = 3
        retry_after = 1  # 1 second TTL for fast expiry in test

        await cache_manager.set_player_status(blizzard_id, check_count, retry_after)
        await asyncio.sleep(2)  # Wait for cooldown to expire

        # Cooldown key expired but status key must still hold check_count
        result = await cache_manager.get_player_status(blizzard_id)
        assert result is not None
        assert result["check_count"] == check_count
        assert result["retry_after"] == 0  # No active cooldown

    @pytest.mark.asyncio
    async def test_exponential_backoff_increments_check_count(
        self, cache_manager: CacheManager
    ):
        """Setting player status multiple times correctly increments check_count"""
        blizzard_id = "backoff-player"

        await cache_manager.set_player_status(blizzard_id, 1, 600)
        await cache_manager.set_player_status(blizzard_id, 2, 1800)

        result = await cache_manager.get_player_status(blizzard_id)
        assert result is not None
        assert result["check_count"] == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_get_player_status_returns_none_when_not_tracked(
        self, cache_manager: CacheManager
    ):
        """Returns None for a player that was never marked unknown"""
        result = await cache_manager.get_player_status("NeverUnknown-9999")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_player_status_removes_all_keys(
        self, cache_manager: CacheManager
    ):
        """Deleting player status removes both status and cooldown keys"""
        blizzard_id = "todelete123"
        battletag = "DeleteMe-0000"
        await cache_manager.set_player_status(blizzard_id, 1, 600, battletag=battletag)

        await cache_manager.delete_player_status(blizzard_id)

        assert await cache_manager.get_player_status(blizzard_id) is None
        assert await cache_manager.get_player_status(battletag) is None

    @pytest.mark.asyncio
    async def test_evict_volatile_data_keeps_unknown_player_keys(
        self, cache_manager: CacheManager
    ):
        """evict_volatile_data removes api-cache keys but preserves unknown-player keys"""
        blizzard_id = "keep-me"
        await cache_manager.set_player_status(blizzard_id, 1, 3600)
        await cache_manager.update_api_cache("/heroes", [{"name": "Ana"}], 3600)

        await cache_manager.evict_volatile_data()

        # api-cache key should be gone
        assert await cache_manager.get_api_cache("/heroes") is None
        # unknown-player status/cooldown should survive
        result = await cache_manager.get_player_status(blizzard_id)
        assert result is not None
        assert result["check_count"] == 1
