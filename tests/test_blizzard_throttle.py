"""Unit tests for BlizzardThrottle adaptive rate limiter."""

import time
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.blizzard.throttle import BlizzardThrottle
from app.config import settings
from app.domain.exceptions import RateLimitedError
from app.metaclasses import Singleton


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the BlizzardThrottle Singleton between tests."""
    Singleton.clear_all()
    yield
    Singleton.clear_all()


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def throttle(mock_cache):
    with patch(
        "app.adapters.blizzard.throttle.ValkeyCache",
        return_value=mock_cache,
    ):
        return BlizzardThrottle()


class TestGetCurrentDelay:
    @pytest.mark.asyncio
    async def test_returns_start_delay_when_no_stored_value(self, throttle, mock_cache):
        mock_cache.get.return_value = None
        delay = await throttle.get_current_delay()
        assert delay == settings.throttle_start_delay

    @pytest.mark.asyncio
    async def test_returns_stored_delay(self, throttle, mock_cache):
        mock_cache.get.return_value = b"5.5"
        delay = await throttle.get_current_delay()
        assert delay == pytest.approx(5.5)


class TestIsRateLimited:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_403_recorded(self, throttle, mock_cache):
        mock_cache.get.return_value = None
        remaining = await throttle.is_rate_limited()
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_penalty_expired(self, throttle, mock_cache):
        # Penalty was more than `penalty_duration` seconds ago
        old_ts = time.time() - settings.throttle_penalty_duration - 5
        mock_cache.get.return_value = str(old_ts).encode()
        remaining = await throttle.is_rate_limited()
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_returns_remaining_during_penalty(self, throttle, mock_cache):
        # 403 happened 10 seconds ago
        recent_ts = time.time() - 10
        mock_cache.get.return_value = str(recent_ts).encode()
        remaining = await throttle.is_rate_limited()
        expected = settings.throttle_penalty_duration - 10
        assert expected - 2 <= remaining <= expected


class TestWaitBeforeRequest:
    @pytest.mark.asyncio
    async def test_raises_rate_limited_error_during_penalty(self, throttle, mock_cache):
        recent_ts = time.time() - 5
        mock_cache.get.return_value = str(recent_ts).encode()
        with pytest.raises(RateLimitedError) as exc_info:
            await throttle.wait_before_request()
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_no_sleep_when_enough_time_elapsed(self, throttle, mock_cache):
        # No penalty, last request was long ago
        def get_side_effect(key):
            if "last_403" in key:
                return None
            if "delay" in key:
                return b"2.0"
            if "last_request" in key:
                return str(time.time() - 10).encode()
            return None

        mock_cache.get.side_effect = get_side_effect

        with patch("asyncio.sleep") as mock_sleep:
            await throttle.wait_before_request()
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_sleeps_when_request_too_soon(self, throttle, mock_cache):
        def get_side_effect(key):
            if "last_403" in key:
                return None
            if "delay" in key:
                return b"5.0"
            if "last_request" in key:
                return str(time.time() - 1).encode()  # only 1s ago, delay is 5s
            return None

        mock_cache.get.side_effect = get_side_effect

        with patch("asyncio.sleep") as mock_sleep:
            await throttle.wait_before_request()
            mock_sleep.assert_called_once()
            wait_time = mock_sleep.call_args[0][0]
            assert 3.5 < wait_time < 4.5  # noqa: PLR2004  # ~4 seconds remaining


class TestAdjustDelay:
    @pytest.mark.asyncio
    async def test_403_applies_penalty(self, throttle, mock_cache):
        mock_cache.get.return_value = b"2.0"
        await throttle.adjust_delay(0.5, HTTPStatus.FORBIDDEN)
        # Should have called set for delay key and last_403 key
        assert mock_cache.set.call_count == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_403_doubles_delay_with_minimum(self, throttle, mock_cache):
        mock_cache.get.return_value = b"2.0"
        await throttle.adjust_delay(0.5, HTTPStatus.FORBIDDEN)
        # First set call should be the new delay
        delay_call = mock_cache.set.call_args_list[0]
        new_delay = float(delay_call[0][1])
        assert new_delay == max(2.0 * 2, settings.throttle_penalty_delay)

    @pytest.mark.asyncio
    async def test_200_adjusts_autothrottle(self, throttle, mock_cache):
        """On 200, delay converges toward latency / target_concurrency."""

        def get_side_effect(key):
            if "last_403" in key:
                return None  # no penalty
            return b"4.0"  # current delay

        mock_cache.get.side_effect = get_side_effect

        await throttle.adjust_delay(1.0, HTTPStatus.OK)
        mock_cache.set.assert_called_once()
        new_delay = float(mock_cache.set.call_args[0][1])
        # target = 1.0 / 0.5 = 2.0; smoothed = max(2.0, (4.0 + 2.0) / 2) = 3.0
        assert new_delay == pytest.approx(3.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_200_does_not_adjust_during_penalty(self, throttle, mock_cache):
        """During penalty, 200 responses do not decrease the delay."""

        def get_side_effect(key):
            if "last_403" in key:
                return str(time.time() - 5).encode()  # active penalty
            return b"10.0"

        mock_cache.get.side_effect = get_side_effect

        await throttle.adjust_delay(0.1, HTTPStatus.OK)
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_200_only_increases_delay(self, throttle, mock_cache):
        """On non-200 (not 403), delay only increases, never decreases."""

        def get_side_effect(key):
            if "last_403" in key:
                return None
            return b"2.0"

        mock_cache.get.side_effect = get_side_effect

        # High latency → should increase
        await throttle.adjust_delay(3.0, HTTPStatus.SERVICE_UNAVAILABLE)
        mock_cache.set.assert_called_once()
        new_delay = float(mock_cache.set.call_args[0][1])
        assert new_delay > 2.0  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_non_200_does_not_decrease(self, throttle, mock_cache):
        """On non-200, if target < current, delay stays the same."""

        def get_side_effect(key):
            if "last_403" in key:
                return None
            return b"10.0"

        mock_cache.get.side_effect = get_side_effect

        # Low latency → target < current → no change
        await throttle.adjust_delay(0.5, HTTPStatus.SERVICE_UNAVAILABLE)
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_delay_respects_max_bound(self, throttle, mock_cache):
        mock_cache.get.return_value = str(settings.throttle_max_delay).encode()
        # 403 on max delay → should stay at max
        await throttle.adjust_delay(0.5, HTTPStatus.FORBIDDEN)
        delay_call = mock_cache.set.call_args_list[0]
        new_delay = float(delay_call[0][1])
        assert new_delay == settings.throttle_max_delay

    @pytest.mark.asyncio
    async def test_delay_respects_min_bound(self, throttle, mock_cache):
        def get_side_effect(key):
            if "last_403" in key:
                return None
            return b"0.01"  # below min

        mock_cache.get.side_effect = get_side_effect

        # Very fast response → target below min → should floor at min
        await throttle.adjust_delay(0.001, HTTPStatus.OK)
        mock_cache.set.assert_called_once()
        new_delay = float(mock_cache.set.call_args[0][1])
        assert new_delay >= settings.throttle_min_delay
