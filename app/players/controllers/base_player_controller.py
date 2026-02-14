"""Base Player Controller module"""

import time
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status

from app.config import settings
from app.controllers import AbstractController
from app.overfast_logger import logger


class BasePlayerController(AbstractController):
    """Base Player Controller used in order to ensure specific exceptions
    are properly handled. For instance, not found players should be cached
    to prevent spamming Blizzard with calls.
    """

    # Player Profile Cache Methods (SQLite-based, replacing Valkey Player Cache)

    async def get_player_profile_cache(
        self, player_id: str
    ) -> dict[str, str | dict] | None:
        """
        Get player profile from persistent storage.
        Returns dict compatible with old Valkey cache format: {"summary": {...}, "profile": "..."}

        Args:
            player_id: Player identifier (BattleTag)

        Returns:
            Dict with 'summary' and 'profile' keys, or None if not found
        """
        profile = await self.storage.get_player_profile(player_id)
        if not profile:
            return None

        # Convert storage format to cache format for backward compatibility
        # Note: We don't have full summary, but we have the key field: lastUpdated
        return {
            "profile": profile["html"],
            "summary": {
                "lastUpdated": profile.get("last_updated_blizzard"),
                "url": profile.get("blizzard_id"),
            },
        }

    async def update_player_profile_cache(
        self,
        player_id: str,
        player_summary: dict,
        html: str,
    ) -> None:
        """
        Update player profile in persistent storage.

        Args:
            player_id: Player identifier (BattleTag)
            player_summary: Summary from search endpoint (contains lastUpdated, url)
            html: Raw career page HTML
        """
        await self.storage.put_player_profile(
            player_id=player_id,
            html=html,
            blizzard_id=player_summary.get("url"),
            last_updated_blizzard=player_summary.get("lastUpdated"),
        )

    # Unknown Player Tracking Methods (SQLite-based with exponential backoff)

    def _calculate_retry_after(self, check_count: int) -> int:
        """
        Calculate retry_after time using exponential backoff.

        Formula: min(base * multiplier^(check_count - 1), max)
        Example: 600 * 3^0 = 600s (10min), 600 * 3^1 = 1800s (30min), etc.

        Args:
            check_count: Number of failed checks

        Returns:
            Seconds to wait before next check (capped at max)
        """
        base = settings.unknown_player_initial_retry
        multiplier = settings.unknown_player_retry_multiplier
        max_retry = settings.unknown_player_max_retry

        retry_after = base * (multiplier ** (check_count - 1))
        return min(int(retry_after), max_retry)

    async def check_unknown_player(self, player_id: str) -> None:
        """
        Check if player is known to not exist and raise 404 if so.
        Uses exponential backoff to reduce checks over time.

        Args:
            player_id: Player ID to check

        Raises:
            HTTPException: 404 if player is still in retry window
        """
        if not settings.unknown_players_cache_enabled:
            return

        player_status = await self.storage.get_player_status(player_id)
        if not player_status:
            return  # Player not marked as unknown

        # Check if retry window has passed
        now = int(time.time())
        time_since_check = now - player_status["last_checked_at"]

        if time_since_check < player_status["retry_after"]:
            # Still in retry window - player is considered unknown
            logger.warning(
                f"Player {player_id} is unknown (retry in {player_status['retry_after'] - time_since_check}s)",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )
        # Retry window passed - allow recheck by falling through

    async def mark_player_unknown_on_404(
        self, player_id: str, exception: HTTPException
    ) -> None:
        """
        Mark player as unknown if 404 exception is raised.
        Implements exponential backoff for retries.

        Args:
            player_id: Player ID to mark
            exception: HTTPException to check for 404 status
        """
        if not settings.unknown_players_cache_enabled:
            return

        if exception.status_code == status.HTTP_404_NOT_FOUND:
            # Get existing status to increment check count
            player_status = await self.storage.get_player_status(player_id)
            check_count = player_status["check_count"] + 1 if player_status else 1

            # Calculate exponential backoff
            retry_after = self._calculate_retry_after(check_count)

            # Store updated status
            await self.storage.set_player_status(player_id, check_count, retry_after)

            logger.info(
                f"Marked player {player_id} as unknown (check #{check_count}, retry in {retry_after}s)"
            )

    async def with_unknown_player_guard(
        self,
        player_id: str,
        handler: Callable[[], Awaitable[dict]],
    ) -> dict:
        """
        Execute handler with unknown player caching guard.
        Checks if player is unknown before calling handler,
        and marks player as unknown if 404 is raised.

        Args:
            player_id: Player ID
            handler: Async function to execute

        Returns:
            Result from handler

        Raises:
            HTTPException: 404 if player is unknown or becomes unknown
        """
        # Check if player is known to not exist
        await self.check_unknown_player(player_id)

        # Execute handler and intercept 404 to mark player unknown
        try:
            return await handler()
        except HTTPException as err:
            await self.mark_player_unknown_on_404(player_id, err)
            raise

    async def process_request(self, **kwargs) -> dict:
        """Process request as usual, but ensure to properly handle players
        we already know aren't existing to prevent spamming Blizzard.
        Uses exponential backoff for unknown players.
        """

        # Ensure unknown players caching system is enabled
        if not settings.unknown_players_cache_enabled:
            return cast("dict", await super().process_request(**kwargs))

        # First check if player is known to not exist (with exponential backoff)
        player_id = kwargs["player_id"]
        await self.check_unknown_player(player_id)

        # Then run process as usual, but intercept HTTP 404 to be able
        # to store result in cache, to prevent calling Blizzard next time
        try:
            return cast("dict", await super().process_request(**kwargs))
        except HTTPException as err:
            await self.mark_player_unknown_on_404(player_id, err)
            raise
