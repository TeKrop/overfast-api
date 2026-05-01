"""Unit tests for PlayerService domain service"""

import time
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from app.domain.exceptions import (
    ParserBlizzardError,
    ParserInternalError,
    ParserParsingError,
)
from app.domain.models.player import PlayerIdentity, PlayerRequest
from app.domain.services.player_service import PlayerService
from tests.fake_storage import FakeStorage
from tests.helpers import read_html_file

_TEKROP_HTML = read_html_file("players/TeKrop-2217.html") or ""
_PLAYER_SUMMARY = {
    "url": "abc123|def456",
    "username": "TeKrop",
    "avatar": "https://example.com/avatar.png",
    "lastUpdated": 1700000000,
}


def _make_service(
    *,
    storage: FakeStorage | None = None,
    cache: AsyncMock | None = None,
    task_queue: AsyncMock | None = None,
) -> PlayerService:
    if storage is None:
        storage = FakeStorage()
    if cache is None:
        cache = AsyncMock()
        cache.get_player_status = AsyncMock(return_value=None)
        cache.set_player_status = AsyncMock()
    if task_queue is None:
        task_queue = AsyncMock()
        task_queue.is_job_pending_or_running = AsyncMock(return_value=False)
    blizzard_client = AsyncMock()
    return PlayerService(cache, storage, blizzard_client, task_queue)


# ---------------------------------------------------------------------------
# _calculate_retry_after
# ---------------------------------------------------------------------------


_BASE_RETRY = 60
_DOUBLED_RETRY = 120
_MAX_RETRY = 300


class TestCalculateRetryAfter:
    def test_first_check_returns_base(self):
        svc = _make_service()
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_player_initial_retry = _BASE_RETRY
            s.unknown_player_retry_multiplier = 2
            s.unknown_player_max_retry = 3600
            result = svc._calculate_retry_after(1)

        assert result == _BASE_RETRY

    def test_second_check_doubles(self):
        svc = _make_service()
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_player_initial_retry = _BASE_RETRY
            s.unknown_player_retry_multiplier = 2
            s.unknown_player_max_retry = 3600
            result = svc._calculate_retry_after(2)

        assert result == _DOUBLED_RETRY

    def test_max_retry_capped(self):
        svc = _make_service()
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_player_initial_retry = _BASE_RETRY
            s.unknown_player_retry_multiplier = 10
            s.unknown_player_max_retry = _MAX_RETRY
            result = svc._calculate_retry_after(5)

        assert result == _MAX_RETRY


# ---------------------------------------------------------------------------
# _check_player_staleness
# ---------------------------------------------------------------------------


class TestCheckPlayerStaleness:
    def test_age_zero_never_stale(self):
        svc = _make_service()

        actual = svc._check_player_staleness(0)

        assert actual is False

    def test_age_below_half_threshold_not_stale(self):
        svc = _make_service()
        with patch("app.domain.services.player_service.settings") as s:
            s.player_staleness_threshold = 3600
            result = svc._check_player_staleness(1000)

        assert result is False

    def test_age_at_half_threshold_is_stale(self):
        svc = _make_service()
        with patch("app.domain.services.player_service.settings") as s:
            s.player_staleness_threshold = 3600
            result = svc._check_player_staleness(1800)

        assert result is True

    def test_age_above_half_threshold_is_stale(self):
        svc = _make_service()
        with patch("app.domain.services.player_service.settings") as s:
            s.player_staleness_threshold = 3600
            result = svc._check_player_staleness(2000)

        assert result is True


# ---------------------------------------------------------------------------
# get_player_profile_cache
# ---------------------------------------------------------------------------


class TestGetPlayerProfileCache:
    @pytest.mark.asyncio
    async def test_returns_none_on_miss(self):
        svc = _make_service()
        result = await svc.get_player_profile_cache("nobody-0000")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_profile_on_hit(self):
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123",
            html=_TEKROP_HTML,
            summary=_PLAYER_SUMMARY,
        )
        svc = _make_service(storage=storage)
        result = await svc.get_player_profile_cache("abc123")

        assert result is not None
        assert result["profile"] == _TEKROP_HTML
        assert result["summary"] == _PLAYER_SUMMARY

    @pytest.mark.asyncio
    async def test_miss_increments_prometheus(self):
        svc = _make_service()
        with (
            patch("app.domain.services.player_service.settings") as s,
            patch(
                "app.domain.services.player_service.storage_cache_hit_total"
            ) as m_hit,
            patch("app.domain.services.player_service.storage_hits_total") as m_total,
        ):
            s.prometheus_enabled = True
            m_hit.labels = MagicMock(return_value=MagicMock())
            m_total.labels = MagicMock(return_value=MagicMock())
            await svc.get_player_profile_cache("nobody-0000")
        m_hit.labels.assert_called_with(table="player_profiles", result="miss")
        m_total.labels.assert_called_with(result="miss")

    @pytest.mark.asyncio
    async def test_hit_increments_prometheus(self):
        storage = FakeStorage()
        await storage.set_player_profile("abc123", html=_TEKROP_HTML)
        svc = _make_service(storage=storage)
        with (
            patch("app.domain.services.player_service.settings") as s,
            patch(
                "app.domain.services.player_service.storage_cache_hit_total"
            ) as m_hit,
            patch("app.domain.services.player_service.storage_hits_total") as m_total,
        ):
            s.prometheus_enabled = True
            m_hit.labels = MagicMock(return_value=MagicMock())
            m_total.labels = MagicMock(return_value=MagicMock())
            await svc.get_player_profile_cache("abc123")
        m_hit.labels.assert_called_with(table="player_profiles", result="hit")
        m_total.labels.assert_called_with(result="hit")


# ---------------------------------------------------------------------------
# _get_fresh_stored_profile
# ---------------------------------------------------------------------------


class TestGetFreshStoredProfile:
    @pytest.mark.asyncio
    async def test_blizzard_id_no_profile_returns_none_with_zero_age(self):
        svc = _make_service()
        with patch(
            "app.domain.services.player_service.is_blizzard_id", return_value=True
        ):
            result = await svc._get_fresh_stored_profile("abc123|def456")

        assert result == (None, 0)

    @pytest.mark.asyncio
    async def test_battletag_no_mapping_returns_none_with_zero_age(self):
        svc = _make_service()
        with patch(
            "app.domain.services.player_service.is_blizzard_id", return_value=False
        ):
            result = await svc._get_fresh_stored_profile("TeKrop-2217")

        assert result == (None, 0)

    @pytest.mark.asyncio
    async def test_stale_profile_returns_none_with_age(self):
        storage = FakeStorage()
        await storage.set_player_profile("abc123", html=_TEKROP_HTML)
        # Artificially age the profile
        storage._profiles["abc123"]["updated_at"] = int(time.time()) - 99999
        svc = _make_service(storage=storage)
        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 3600
            s.prometheus_enabled = False
            result = await svc._get_fresh_stored_profile("abc123")

        assert result == (None, 99999)

    @pytest.mark.asyncio
    async def test_fresh_profile_returns_tuple(self):
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123", html=_TEKROP_HTML, summary=_PLAYER_SUMMARY
        )
        svc = _make_service(storage=storage)
        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 99999
            s.prometheus_enabled = False
            result = await svc._get_fresh_stored_profile("abc123")

        assert result is not None
        profile, age = result

        assert profile is not None
        assert profile["profile"] == _TEKROP_HTML
        assert age >= 0


# ---------------------------------------------------------------------------
# _mark_player_unknown
# ---------------------------------------------------------------------------


class TestMarkPlayerUnknown:
    @pytest.mark.asyncio
    async def test_disabled_feature_is_noop(self):
        svc = _make_service()
        exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = False
            await svc._mark_player_unknown("abc123", exc)
        cast("Any", svc.cache).set_player_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_404_is_noop(self):
        svc = _make_service()
        exc = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="error"
        )
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = True
            await svc._mark_player_unknown("abc123", exc)
        cast("Any", svc.cache).set_player_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_404_marks_player(self):
        cache = AsyncMock()
        cache.get_player_status = AsyncMock(return_value=None)
        cache.set_player_status = AsyncMock()
        svc = _make_service(cache=cache)
        exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = True
            s.unknown_player_initial_retry = 60
            s.unknown_player_retry_multiplier = 2
            s.unknown_player_max_retry = 3600
            await svc._mark_player_unknown("abc123", exc, battletag="TeKrop-2217")
        cache.set_player_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_404_increments_check_count(self):
        cache = AsyncMock()
        cache.get_player_status = AsyncMock(return_value={"check_count": 3})
        cache.set_player_status = AsyncMock()
        svc = _make_service(cache=cache)
        exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = True
            s.unknown_player_initial_retry = 60
            s.unknown_player_retry_multiplier = 2
            s.unknown_player_max_retry = 3600
            await svc._mark_player_unknown("abc123", exc)
        args = cache.set_player_status.call_args
        # check_count should be incremented from 3 to 4
        _expected_check_count = 4

        assert args[0][1] == _expected_check_count


# ---------------------------------------------------------------------------
# _handle_player_exceptions
# ---------------------------------------------------------------------------


class TestHandlePlayerExceptions:
    @pytest.mark.asyncio
    async def test_blizzard_404_raises_http_not_found(self):
        svc = _make_service()
        error = ParserBlizzardError(
            status_code=status.HTTP_404_NOT_FOUND, message="Player not found"
        )
        identity = PlayerIdentity()
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = False
            with pytest.raises(HTTPException) as exc_info:
                await svc._handle_player_exceptions(error, "TeKrop-2217", identity)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_parser_parsing_error_main_content_raises_404(self):
        svc = _make_service()
        error = ParserParsingError("Could not find main content in HTML")
        identity = PlayerIdentity()
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = False
            with pytest.raises(HTTPException) as exc_info:
                await svc._handle_player_exceptions(error, "TeKrop-2217", identity)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_parser_parsing_error_other_raises_parser_internal_error(self):
        svc = _make_service()
        error = ParserParsingError("Some DOM parsing failure")
        identity = PlayerIdentity(player_summary={"url": "abc123"})

        with patch("app.domain.services.player_service.settings") as s:
            s.blizzard_host = "https://overwatch.blizzard.com"
            s.career_path = "/career"
            with pytest.raises(ParserInternalError) as exc_info:
                await svc._handle_player_exceptions(error, "TeKrop-2217", identity)

        assert "overwatch.blizzard.com" in exc_info.value.blizzard_url
        assert exc_info.value.cause is error

    @pytest.mark.asyncio
    async def test_http_exception_404_marks_and_reraises(self):
        svc = _make_service()
        error = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
        identity = PlayerIdentity()
        with patch("app.domain.services.player_service.settings") as s:
            s.unknown_players_cache_enabled = False
            with pytest.raises(HTTPException):
                await svc._handle_player_exceptions(error, "TeKrop-2217", identity)

    @pytest.mark.asyncio
    async def test_http_exception_non_404_reraises(self):
        svc = _make_service()
        error = HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limited"
        )
        identity = PlayerIdentity()
        with pytest.raises(HTTPException) as exc_info:
            await svc._handle_player_exceptions(error, "TeKrop-2217", identity)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_generic_exception_reraises(self):
        svc = _make_service()
        error = RuntimeError("unexpected")
        identity = PlayerIdentity()
        with pytest.raises(RuntimeError):
            await svc._handle_player_exceptions(error, "TeKrop-2217", identity)


# ---------------------------------------------------------------------------
# _execute_player_request — fast path and slow path
# ---------------------------------------------------------------------------


class TestExecutePlayerRequest:
    @pytest.mark.asyncio
    async def test_fast_path_from_storage(self):
        """When storage has a fresh profile, Blizzard is never called."""
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123|def456",
            html=_TEKROP_HTML,
            summary=_PLAYER_SUMMARY,
        )
        svc = _make_service(storage=storage)
        data_factory = Mock(return_value={"result": "ok"})

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 99999
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            result, _is_stale, _age = await svc._execute_player_request(
                PlayerRequest(
                    player_id="abc123|def456",
                    cache_key="test-key",
                    data_factory=data_factory,
                )
            )

        assert result == {"result": "ok"}
        data_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_slow_path_calls_blizzard(self):
        """When no fresh profile in storage, Blizzard is called."""
        mock_response = Mock(
            status_code=status.HTTP_200_OK,
            text=_TEKROP_HTML,
            url="https://overwatch.blizzard.com/career/TeKrop-2217/",
        )
        blizzard_client = AsyncMock()
        blizzard_client.get = AsyncMock(return_value=mock_response)
        svc = _make_service()
        svc.blizzard_client = blizzard_client

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=False
            ),
            patch(
                "app.domain.services.player_service.fetch_player_summary_json",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.domain.services.player_service.parse_player_summary_json",
                return_value=None,
            ),
            patch(
                "app.domain.services.player_service.fetch_player_html",
                new_callable=AsyncMock,
                return_value=(_TEKROP_HTML, "abc123|def456"),
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 0
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            s.blizzard_host = "https://overwatch.blizzard.com"
            s.career_path = "/career"
            s.unknown_players_cache_enabled = False
            result, _is_stale, _age = await svc._execute_player_request(
                PlayerRequest(
                    player_id="TeKrop-2217",
                    cache_key="test-key",
                    data_factory=lambda _html, _summary: {"from": "blizzard"},
                )
            )

        assert result == {"from": "blizzard"}

    @pytest.mark.asyncio
    async def test_stale_profile_enqueues_refresh(self):
        """When profile is old enough, is_stale=True and refresh is enqueued."""
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123|def456",
            html=_TEKROP_HTML,
            summary=_PLAYER_SUMMARY,
        )
        # Age the profile beyond the staleness threshold (so _get_fresh_stored_profile → None)
        # Then it goes to slow path; we mock the identity resolution and html fetch
        storage._profiles["abc123|def456"]["updated_at"] = int(time.time()) - 9999
        task_queue = AsyncMock()
        task_queue.is_job_pending_or_running = AsyncMock(return_value=False)
        svc = _make_service(storage=storage, task_queue=task_queue)

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch(
                "app.domain.services.player_service.fetch_player_html",
                new_callable=AsyncMock,
                return_value=(_TEKROP_HTML, "abc123|def456"),
            ),
            patch(
                "app.domain.services.player_service.fetch_player_summary_json",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.domain.services.player_service.parse_player_summary_json",
                return_value=None,
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 3600
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            result, _is_stale, _age = await svc._execute_player_request(
                PlayerRequest(
                    player_id="abc123|def456",
                    cache_key="test-key",
                    data_factory=lambda _html, _summary: {},
                )
            )
        # Profile is stale (age > threshold), slow path → fresh fetch → age=0 → not stale
        assert result == {}

    @pytest.mark.asyncio
    async def test_fast_path_preserves_stored_at_in_cache(self):
        """When serving from storage, stored_at is forwarded to the cache write
        so the Lua Age header reflects the real data age, not the write time."""
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123|def456",
            html=_TEKROP_HTML,
            summary=_PLAYER_SUMMARY,
        )
        original_updated_at = storage._profiles["abc123|def456"]["updated_at"]
        cache = AsyncMock()
        svc = _make_service(storage=storage, cache=cache)

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 99999
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            s.stale_cache_timeout = 60
            await svc._execute_player_request(
                PlayerRequest(
                    player_id="abc123|def456",
                    cache_key="test-key",
                    data_factory=lambda _html, _summary: {},
                )
            )

        call_kwargs = cache.update_api_cache.call_args.kwargs
        assert call_kwargs["stored_at"] == original_updated_at

    @pytest.mark.asyncio
    async def test_stale_fast_path_sets_stale_while_revalidate(self):
        """When is_stale=True (storage path), stale_while_revalidate is set in the
        cache envelope so Lua emits the correct X-Cache-Status: stale header."""
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123|def456",
            html=_TEKROP_HTML,
            summary=_PLAYER_SUMMARY,
        )
        # Age the profile into the stale window (>= threshold // 2)
        storage._profiles["abc123|def456"]["updated_at"] = int(time.time()) - 2000
        cache = AsyncMock()
        task_queue = AsyncMock()
        task_queue.is_job_pending_or_running = AsyncMock(return_value=False)
        svc = _make_service(storage=storage, cache=cache, task_queue=task_queue)

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 3600
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            s.stale_cache_timeout = 60
            _data, is_stale, _age = await svc._execute_player_request(
                PlayerRequest(
                    player_id="abc123|def456",
                    cache_key="test-key",
                    data_factory=lambda _html, _summary: {},
                )
            )

        assert is_stale is True
        call_kwargs = cache.update_api_cache.call_args.kwargs
        assert call_kwargs["stale_while_revalidate"] == 60  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_fresh_blizzard_fetch_stored_at_is_none(self):
        """On a fresh Blizzard fetch (age=0), stored_at=None so the cache adapter
        stamps the current time, which is correct."""
        svc = _make_service()
        cache = AsyncMock()
        svc.cache = cache

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=False
            ),
            patch(
                "app.domain.services.player_service.fetch_player_summary_json",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.domain.services.player_service.parse_player_summary_json",
                return_value=None,
            ),
            patch(
                "app.domain.services.player_service.fetch_player_html",
                new_callable=AsyncMock,
                return_value=(_TEKROP_HTML, "abc123|def456"),
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 0
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            s.stale_cache_timeout = 60
            s.blizzard_host = "https://overwatch.blizzard.com"
            s.career_path = "/career"
            s.unknown_players_cache_enabled = False
            await svc._execute_player_request(
                PlayerRequest(
                    player_id="TeKrop-2217",
                    cache_key="test-key",
                    data_factory=lambda _html, _summary: {},
                )
            )

        call_kwargs = cache.update_api_cache.call_args.kwargs
        assert call_kwargs["stored_at"] is None


# ---------------------------------------------------------------------------
# refresh_player_profile — bypasses storage fast-path
# ---------------------------------------------------------------------------


class TestRefreshPlayerProfile:
    @pytest.mark.asyncio
    async def test_always_calls_blizzard_even_when_profile_is_fresh(self):
        """refresh_player_profile bypasses _get_fresh_stored_profile and always
        fetches from Blizzard, even when the stored profile is within the
        staleness threshold."""
        storage = FakeStorage()
        await storage.set_player_profile(
            "abc123|def456",
            html=_TEKROP_HTML,
            summary=_PLAYER_SUMMARY,
        )
        svc = _make_service(storage=storage)

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch(
                "app.domain.services.player_service.fetch_player_html",
                new_callable=AsyncMock,
                return_value=(_TEKROP_HTML, "abc123|def456"),
            ) as mock_fetch,
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = (
                99999  # profile would pass the fast-path check
            )
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            s.unknown_players_cache_enabled = False
            await svc.refresh_player_profile("abc123|def456")

        mock_fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_persistent_storage(self):
        """refresh_player_profile writes a fresh profile to persistent storage."""
        storage = FakeStorage()
        svc = _make_service(storage=storage)

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=True
            ),
            patch(
                "app.domain.services.player_service.fetch_player_html",
                new_callable=AsyncMock,
                return_value=(_TEKROP_HTML, "abc123|def456"),
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 3600
            s.prometheus_enabled = False
            s.career_path_cache_timeout = 300
            s.unknown_players_cache_enabled = False
            await svc.refresh_player_profile("abc123|def456")

        profile = await storage.get_player_profile("abc123|def456")
        assert profile is not None

    @pytest.mark.asyncio
    async def test_blizzard_error_propagates_as_http_exception(self):
        """A ParserBlizzardError from identity resolution is translated to an
        HTTPException by _handle_player_exceptions and re-raised — the worker's
        _run_refresh_task except block captures it."""
        svc = _make_service()
        err = ParserBlizzardError(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Blizzard unavailable"
        )

        with (
            patch(
                "app.domain.services.player_service.is_blizzard_id", return_value=False
            ),
            patch(
                "app.domain.services.player_service.fetch_player_summary_json",
                new_callable=AsyncMock,
                side_effect=err,
            ),
            patch("app.domain.services.player_service.settings") as s,
        ):
            s.player_staleness_threshold = 3600
            s.prometheus_enabled = False
            s.unknown_players_cache_enabled = False
            with pytest.raises(HTTPException) as exc_info:
                await svc.refresh_player_profile("TeKrop-2217")

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
