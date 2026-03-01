"""Unit tests for BlizzardThrottle adaptive rate limiter."""

import time
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.blizzard.throttle import (
    _DELAY_KEY,
    _LAST_403_KEY,
    _SSTHRESH_KEY,
    _STREAK_KEY,
    BlizzardThrottle,
)
from app.config import settings
from app.domain.exceptions import RateLimitedError
from app.infrastructure.metaclasses import Singleton


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
    async def test_403_sets_penalty_and_ssthresh(self, throttle, mock_cache):
        """403 should double delay, set ssthresh, reset streak, record last_403."""
        mock_cache.get.return_value = b"2.0"
        await throttle.adjust_delay(HTTPStatus.FORBIDDEN)
        # delay set + last_403 set (at minimum 2 set calls)
        keys_set = [call[0][0] for call in mock_cache.set.call_args_list]
        assert _DELAY_KEY in keys_set
        assert _LAST_403_KEY in keys_set
        assert _SSTHRESH_KEY in keys_set
        assert _STREAK_KEY in keys_set

    @pytest.mark.asyncio
    async def test_403_doubles_delay_with_minimum(self, throttle, mock_cache):
        mock_cache.get.return_value = b"2.0"
        await throttle.adjust_delay(HTTPStatus.FORBIDDEN)
        delay_set = next(
            float(c[0][1]) for c in mock_cache.set.call_args_list if c[0][0] == _DELAY_KEY
        )
        assert delay_set == max(4.0, settings.throttle_penalty_delay)

    @pytest.mark.asyncio
    async def test_403_sets_ssthresh_to_double_current(self, throttle, mock_cache):
        mock_cache.get.return_value = b"2.0"
        await throttle.adjust_delay(HTTPStatus.FORBIDDEN)
        ssthresh_set = next(
            float(c[0][1]) for c in mock_cache.set.call_args_list if c[0][0] == _SSTHRESH_KEY
        )
        assert ssthresh_set == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_200_slow_start_halves_delay_after_n_successes(self, throttle, mock_cache):
        """In slow start (delay > ssthresh), delay halves every N successes."""
        # delay=4.0, ssthresh=1.0 (default min), streak reaching threshold
        def get_side_effect(key):
            if key == _LAST_403_KEY:
                return None
            if key == _DELAY_KEY:
                return b"4.0"
            if key == _SSTHRESH_KEY:
                return b"1.0"
            if key == _STREAK_KEY:
                return str(settings.throttle_slow_start_n_successes - 1).encode()
            return None

        mock_cache.get.side_effect = get_side_effect
        await throttle.adjust_delay(HTTPStatus.OK)

        delay_set = next(
            float(c[0][1]) for c in mock_cache.set.call_args_list if c[0][0] == _DELAY_KEY
        )
        assert delay_set == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_200_slow_start_no_change_below_n_successes(self, throttle, mock_cache):
        """In slow start, delay does not change if streak < N."""
        def get_side_effect(key):
            if key == _LAST_403_KEY:
                return None
            if key == _DELAY_KEY:
                return b"4.0"
            if key == _SSTHRESH_KEY:
                return b"1.0"
            if key == _STREAK_KEY:
                return b"3"
            return None

        mock_cache.get.side_effect = get_side_effect
        await throttle.adjust_delay(HTTPStatus.OK)

        keys_set = [c[0][0] for c in mock_cache.set.call_args_list]
        assert _DELAY_KEY not in keys_set

    @pytest.mark.asyncio
    async def test_200_aimd_decreases_delay_after_m_successes(self, throttle, mock_cache):
        """In AIMD phase (delay <= ssthresh), delay decreases by delta every M successes."""
        def get_side_effect(key):
            if key == _LAST_403_KEY:
                return None
            if key == _DELAY_KEY:
                return b"0.5"
            if key == _SSTHRESH_KEY:
                return b"1.0"
            if key == _STREAK_KEY:
                return str(settings.throttle_aimd_n_successes - 1).encode()
            return None

        mock_cache.get.side_effect = get_side_effect
        await throttle.adjust_delay(HTTPStatus.OK)

        delay_set = next(
            float(c[0][1]) for c in mock_cache.set.call_args_list if c[0][0] == _DELAY_KEY
        )
        assert delay_set == pytest.approx(0.5 - settings.throttle_aimd_delta)

    @pytest.mark.asyncio
    async def test_200_aimd_no_change_below_m_successes(self, throttle, mock_cache):
        """In AIMD phase, delay does not change if streak < M."""
        def get_side_effect(key):
            if key == _LAST_403_KEY:
                return None
            if key == _DELAY_KEY:
                return b"0.5"
            if key == _SSTHRESH_KEY:
                return b"1.0"
            if key == _STREAK_KEY:
                return b"3"
            return None

        mock_cache.get.side_effect = get_side_effect
        await throttle.adjust_delay(HTTPStatus.OK)

        keys_set = [c[0][0] for c in mock_cache.set.call_args_list]
        assert _DELAY_KEY not in keys_set

    @pytest.mark.asyncio
    async def test_200_during_penalty_does_nothing(self, throttle, mock_cache):
        """During penalty, 200 responses do not change delay or streak."""
        def get_side_effect(key):
            if key == _LAST_403_KEY:
                return str(time.time() - 5).encode()  # active penalty
            return b"10.0"

        mock_cache.get.side_effect = get_side_effect
        await throttle.adjust_delay(HTTPStatus.OK)
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_200_resets_streak_only(self, throttle, mock_cache):
        """Non-200, non-403 responses only reset the streak."""
        mock_cache.get.return_value = b"2.0"
        await throttle.adjust_delay(HTTPStatus.SERVICE_UNAVAILABLE)
        keys_set = [c[0][0] for c in mock_cache.set.call_args_list]
        assert keys_set == [_STREAK_KEY]

    @pytest.mark.asyncio
    async def test_delay_respects_min_bound(self, throttle, mock_cache):
        """AIMD phase: delay never goes below throttle_min_delay."""
        def get_side_effect(key):
            if key == _LAST_403_KEY:
                return None
            if key == _DELAY_KEY:
                return str(settings.throttle_min_delay).encode()
            if key == _SSTHRESH_KEY:
                return str(settings.throttle_min_delay + 0.5).encode()
            if key == _STREAK_KEY:
                return str(settings.throttle_aimd_n_successes - 1).encode()
            return None

        mock_cache.get.side_effect = get_side_effect
        await throttle.adjust_delay(HTTPStatus.OK)

        delay_set_calls = [c for c in mock_cache.set.call_args_list if c[0][0] == _DELAY_KEY]
        if delay_set_calls:
            new_delay = float(delay_set_calls[0][0][1])
            assert new_delay >= settings.throttle_min_delay

    @pytest.mark.asyncio
    async def test_delay_respects_max_bound(self, throttle, mock_cache):
        """403 on max delay stays at max."""
        mock_cache.get.return_value = str(settings.throttle_max_delay).encode()
        await throttle.adjust_delay(HTTPStatus.FORBIDDEN)
        delay_set = next(
            float(c[0][1]) for c in mock_cache.set.call_args_list if c[0][0] == _DELAY_KEY
        )
        assert delay_set == settings.throttle_max_delay
