"""Tests for app/adapters/tasks/worker.py — task functions and helpers"""

import contextlib
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.tasks.worker import (
    _run_refresh_task,
    check_new_hero,
    cleanup_stale_players,
    refresh_gamemodes,
    refresh_hero,
    refresh_heroes,
    refresh_maps,
    refresh_player_profile,
    refresh_roles,
)
from app.domain.enums import HeroKey, Locale


@pytest.fixture(autouse=True)
def mock_worker_metrics():
    """Patch all worker Prometheus metrics for every test in this module."""
    with (
        patch(
            "app.adapters.tasks.worker.background_refresh_completed_total"
        ) as mock_completed,
        patch(
            "app.adapters.tasks.worker.background_refresh_failed_total"
        ) as mock_failed,
        patch(
            "app.adapters.tasks.worker.background_tasks_duration_seconds"
        ) as mock_duration,
    ):
        mock_completed.labels.return_value = MagicMock()
        mock_failed.labels.return_value = MagicMock()
        mock_duration.labels.return_value = MagicMock()
        yield mock_completed, mock_failed, mock_duration


# ── _run_refresh_task ─────────────────────────────────────────────────────────


class TestRunRefreshTask:
    @pytest.mark.asyncio
    async def test_success_increments_completed_counter(self, mock_worker_metrics):
        """On success, background_refresh_completed_total is incremented."""
        mock_completed, mock_failed, _ = mock_worker_metrics
        mock_queue = AsyncMock()

        async with _run_refresh_task("heroes", "heroes:en-us", mock_queue):
            pass

        mock_completed.labels.assert_called_once_with(entity_type="heroes")
        mock_completed.labels.return_value.inc.assert_called_once()
        mock_failed.labels.return_value.inc.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_increments_failed_counter_and_reraises(
        self, mock_worker_metrics
    ):
        """On exception, background_refresh_failed_total is incremented and exception re-raised."""
        mock_completed, mock_failed, _ = mock_worker_metrics
        mock_queue = AsyncMock()

        async def _fail():
            async with _run_refresh_task("maps", "maps:all", mock_queue):
                msg = "task failed"
                raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="task failed"):
            await _fail()

        mock_failed.labels.assert_called_once_with(entity_type="maps")
        mock_failed.labels.return_value.inc.assert_called_once()
        mock_completed.labels.return_value.inc.assert_not_called()

    @pytest.mark.asyncio
    async def test_duration_always_recorded(self, mock_worker_metrics):
        """Duration histogram is observed regardless of success or failure."""
        _, _, mock_duration = mock_worker_metrics
        mock_obs = MagicMock()
        mock_duration.labels.return_value = mock_obs
        mock_queue = AsyncMock()

        async def _raise_in_context():
            async with _run_refresh_task("roles", "roles:en-us", mock_queue):
                msg = "oops"
                raise ValueError(msg)

        with contextlib.suppress(ValueError):
            await _raise_in_context()

        mock_duration.labels.assert_called_once_with(entity_type="roles")
        mock_obs.observe.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_job_called_on_success(self):
        """release_job is called with entity_id after a successful refresh."""
        mock_queue = AsyncMock()

        async with _run_refresh_task("player", "Player-1234", mock_queue):
            pass

        mock_queue.release_job.assert_awaited_once_with("Player-1234")

    @pytest.mark.asyncio
    async def test_release_job_called_on_failure(self):
        """release_job is called with entity_id even when the refresh raises."""
        mock_queue = AsyncMock()

        async def _fail():
            async with _run_refresh_task("hero", "hero:ana:en-us", mock_queue):
                msg = "oops"
                raise RuntimeError(msg)

        with contextlib.suppress(RuntimeError):
            await _fail()

        mock_queue.release_job.assert_awaited_once_with("hero:ana:en-us")


# ── refresh tasks ─────────────────────────────────────────────────────────────


class TestRefreshHeroes:
    @pytest.mark.asyncio
    async def test_calls_service_refresh_list(self):
        mock_service = AsyncMock()
        mock_queue = AsyncMock()

        await cast("Any", refresh_heroes).__wrapped__(
            "heroes:en-us", mock_service, mock_queue
        )

        mock_service.refresh_list.assert_awaited_once_with(Locale.ENGLISH_US)


class TestRefreshHero:
    @pytest.mark.asyncio
    async def test_calls_service_refresh_single(self):
        mock_service = AsyncMock()
        mock_queue = AsyncMock()
        first_key = str(next(iter(HeroKey)))

        await cast("Any", refresh_hero).__wrapped__(
            f"hero:{first_key}:en-us", mock_service, mock_queue
        )

        mock_service.refresh_single.assert_awaited_once_with(
            first_key, Locale.ENGLISH_US
        )


class TestRefreshRoles:
    @pytest.mark.asyncio
    async def test_calls_service_refresh_list(self):
        mock_service = AsyncMock()
        mock_queue = AsyncMock()

        await cast("Any", refresh_roles).__wrapped__(
            "roles:fr-fr", mock_service, mock_queue
        )

        mock_service.refresh_list.assert_awaited_once_with(Locale.FRENCH)


class TestRefreshMaps:
    @pytest.mark.asyncio
    async def test_calls_service_refresh_list(self):
        mock_service = AsyncMock()
        mock_queue = AsyncMock()

        await cast("Any", refresh_maps).__wrapped__(
            "maps:all", mock_service, mock_queue
        )

        mock_service.refresh_list.assert_awaited_once()


class TestRefreshGamemodes:
    @pytest.mark.asyncio
    async def test_calls_service_refresh_list(self):
        mock_service = AsyncMock()
        mock_queue = AsyncMock()

        await cast("Any", refresh_gamemodes).__wrapped__(
            "gamemodes:all", mock_service, mock_queue
        )

        mock_service.refresh_list.assert_awaited_once()


class TestRefreshPlayerProfile:
    @pytest.mark.asyncio
    async def test_calls_service_refresh_player_profile(self):
        mock_service = AsyncMock()
        mock_queue = AsyncMock()

        await cast("Any", refresh_player_profile).__wrapped__(
            "Player-1234", mock_service, mock_queue
        )

        mock_service.refresh_player_profile.assert_awaited_once_with("Player-1234")


# ── cleanup_stale_players ─────────────────────────────────────────────────────


class TestCleanupStalePlayers:
    @pytest.mark.asyncio
    async def test_skipped_when_max_age_zero(self):
        mock_storage = AsyncMock()
        with patch("app.adapters.tasks.worker.settings") as mock_settings:
            mock_settings.player_profile_max_age = 0
            await cast("Any", cleanup_stale_players).__wrapped__(mock_storage)

        mock_storage.delete_old_player_profiles.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_calls_delete_old_player_profiles(self):
        mock_storage = AsyncMock()
        with patch("app.adapters.tasks.worker.settings") as mock_settings:
            mock_settings.player_profile_max_age = 86400
            await cast("Any", cleanup_stale_players).__wrapped__(mock_storage)

        mock_storage.delete_old_player_profiles.assert_awaited_once_with(86400)

    @pytest.mark.asyncio
    async def test_storage_exception_is_swallowed(self):
        mock_storage = AsyncMock()
        mock_storage.delete_old_player_profiles.side_effect = Exception("DB gone")
        with patch("app.adapters.tasks.worker.settings") as mock_settings:
            mock_settings.player_profile_max_age = 3600
            # Should not propagate
            await cast("Any", cleanup_stale_players).__wrapped__(mock_storage)


# ── check_new_hero ────────────────────────────────────────────────────────────


class TestCheckNewHero:
    @pytest.mark.asyncio
    async def test_skipped_when_webhook_disabled(self):
        mock_client = AsyncMock()
        with (
            patch("app.adapters.tasks.worker.settings") as mock_settings,
            patch("app.adapters.tasks.worker.fetch_heroes_html") as mock_fetch,
        ):
            mock_settings.discord_webhook_enabled = False
            await cast("Any", check_new_hero).__wrapped__(mock_client)

        mock_fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_notification_when_no_new_keys(self):
        mock_client = AsyncMock()
        existing_heroes = [{"key": str(k)} for k in HeroKey]

        with (
            patch("app.adapters.tasks.worker.settings") as mock_settings,
            patch(
                "app.adapters.tasks.worker.fetch_heroes_html",
                return_value="<html>",
            ),
            patch(
                "app.adapters.tasks.worker.parse_heroes_html",
                return_value=existing_heroes,
            ),
            patch(
                "app.adapters.tasks.worker.send_discord_webhook_message"
            ) as mock_discord,
        ):
            mock_settings.discord_webhook_enabled = True
            await cast("Any", check_new_hero).__wrapped__(mock_client)

        mock_discord.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_sent_for_new_hero(self):
        mock_client = AsyncMock()
        heroes_with_new = [{"key": str(k)} for k in HeroKey] + [
            {"key": "brand-new-hero"}
        ]

        with (
            patch("app.adapters.tasks.worker.settings") as mock_settings,
            patch(
                "app.adapters.tasks.worker.fetch_heroes_html",
                return_value="<html>",
            ),
            patch(
                "app.adapters.tasks.worker.parse_heroes_html",
                return_value=heroes_with_new,
            ),
            patch(
                "app.adapters.tasks.worker.send_discord_webhook_message"
            ) as mock_discord,
        ):
            mock_settings.discord_webhook_enabled = True
            await cast("Any", check_new_hero).__wrapped__(mock_client)

        mock_discord.assert_called_once()
        call_kwargs = mock_discord.call_args.kwargs
        assert "brand-new-hero" in call_kwargs["fields"][0]["value"]

    @pytest.mark.asyncio
    async def test_fetch_exception_is_swallowed(self):
        mock_client = AsyncMock()
        with (
            patch("app.adapters.tasks.worker.settings") as mock_settings,
            patch(
                "app.adapters.tasks.worker.fetch_heroes_html",
                side_effect=Exception("network error"),
            ),
            patch(
                "app.adapters.tasks.worker.send_discord_webhook_message"
            ) as mock_discord,
        ):
            mock_settings.discord_webhook_enabled = True
            await cast("Any", check_new_hero).__wrapped__(mock_client)

        mock_discord.assert_not_called()
