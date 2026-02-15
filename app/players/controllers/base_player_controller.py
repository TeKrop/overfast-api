"""Base Player Controller module"""

import time
from functools import wraps
from typing import TYPE_CHECKING, cast

from fastapi import HTTPException, status

from app.adapters.blizzard.parsers.player_profile import fetch_player_html
from app.adapters.blizzard.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary_json,
)
from app.adapters.blizzard.parsers.utils import is_blizzard_id
from app.config import settings
from app.controllers import AbstractController
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort


def with_unknown_player_guard(func):
    """
    Decorator to guard player endpoints against unknown players.

    Checks if player is unknown before executing the handler, and marks
    player as unknown on 404. Requires the method to accept player_id in kwargs.

    Example:
        @with_unknown_player_guard
        async def process_request(self, **kwargs) -> dict:
            player_id = kwargs["player_id"]
            # ... handler logic

    Args:
        func: Async method to decorate (must accept **kwargs with player_id)

    Returns:
        Decorated async method with unknown player protection

    Raises:
        HTTPException: 404 if player is unknown or becomes unknown
        ValueError: If player_id is not in kwargs
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs) -> dict:
        player_id = kwargs.get("player_id")
        if not player_id:
            msg = "with_unknown_player_guard requires player_id in kwargs"
            raise ValueError(msg)

        # Check if player is known to not exist
        await self.check_unknown_player(player_id)

        # Execute handler with unknown player marking on 404
        try:
            return await func(self, *args, **kwargs)
        except HTTPException as exception:
            await self.mark_player_unknown_on_404(player_id, exception)
            raise

    return wrapper


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

        # Storage now returns full summary from summary_json column
        return {
            "profile": profile["html"],
            "summary": profile["summary"],  # Full summary with all fields
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
            player_summary: Full summary from search endpoint (all fields)
            html: Raw career page HTML
        """
        await self.storage.set_player_profile(
            player_id=player_id,
            html=html,
            summary=player_summary,  # Store complete summary
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
            # Still in retry window - return detailed 404 response
            retry_after_seconds = player_status["retry_after"] - time_since_check
            next_check_at = (
                player_status["last_checked_at"] + player_status["retry_after"]
            )

            logger.warning(
                f"Player {player_id} is unknown (retry in {retry_after_seconds}s, "
                f"check #{player_status['check_count']})"
            )

            # Return detailed 404 with retry information
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Player not found",
                    "retry_after": retry_after_seconds,
                    "next_check_at": next_check_at,
                    "check_count": player_status["check_count"],
                },
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

    async def _resolve_player_identity(
        self, client: BlizzardClientPort, player_id: str
    ) -> dict:
        """Resolve player identity via search and Blizzard ID redirect if needed.

        This method implements the identity resolution flow:
        1. Skip search if player_id is already a Blizzard ID
        2. Fetch and parse search results
        3. If not found, attempt Blizzard ID resolution via redirect
        4. Re-parse search results with Blizzard ID if obtained

        Args:
            client: Blizzard API client
            player_id: Player identifier (BattleTag or Blizzard ID)

        Returns:
            Player summary dict (may be empty if not found in search or direct Blizzard ID)
        """
        logger.info("Retrieving Player Summary...")

        # Skip search if player_id is already a Blizzard ID
        if is_blizzard_id(player_id):
            logger.info("Player ID is a Blizzard ID, skipping search")
            return {}

        # Fetch and parse search results
        search_json = await fetch_player_summary_json(client, player_id)
        player_summary = parse_player_summary_json(search_json, player_id)

        if player_summary:
            logger.info("Player Summary retrieved!")
            return player_summary

        # Player not found in search - try to resolve via Blizzard ID redirect
        logger.info("Player not found in search, attempting Blizzard ID resolution")
        _, blizzard_id = await fetch_player_html(client, player_id)

        if blizzard_id and search_json:
            logger.info(
                f"Got Blizzard ID from redirect: {blizzard_id}, re-parsing search results"
            )
            player_summary = parse_player_summary_json(
                search_json, player_id, blizzard_id
            )

            if player_summary:
                logger.info("Successfully resolved player via Blizzard ID")
                return player_summary

            logger.warning(
                "Could not resolve player even with Blizzard ID from redirect"
            )

        return {}
