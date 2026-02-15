"""Base Player Controller module"""

import time
from functools import wraps
from typing import TYPE_CHECKING

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

    Checks if player is unknown before executing the handler.
    Requires the method to accept player_id in kwargs.

    Note: Marking unknown is now handled explicitly in controllers (no decorator magic).

    Example:
        @with_unknown_player_guard
        async def process_request(self, **kwargs) -> dict:
            player_id = kwargs["player_id"]
            try:
                # ... handler logic ...
            except HTTPException as exception:
                await self.mark_player_unknown_on_404(blizzard_id, exception, battletag)
                raise

    Args:
        func: Async method to decorate (must accept **kwargs with player_id)

    Returns:
        Decorated async method with unknown player protection

    Raises:
        HTTPException: 404 if player is unknown
        ValueError: If player_id is not in kwargs
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs) -> dict:
        player_id = kwargs.get("player_id")
        if not player_id:
            msg = "with_unknown_player_guard requires player_id in kwargs"
            raise ValueError(msg)

        # Check if player is known to not exist (by Blizzard ID or BattleTag)
        await self.check_unknown_player(player_id)

        # Execute handler (marking unknown is now explicit in handler)
        return await func(self, *args, **kwargs)

    return wrapper


class BasePlayerController(AbstractController):
    """Base Player Controller used in order to ensure specific exceptions
    are properly handled. For instance, not found players should be cached
    to prevent spamming Blizzard with calls.
    """

    # Player Profile Cache Methods (SQLite-based, replacing Valkey Player Cache)

    async def get_player_profile_cache(
        self, player_id: str
    ) -> dict[str, str | dict | None] | None:
        """
        Get player profile from persistent storage.
        Returns dict compatible with old Valkey cache format: {"summary": {...}, "profile": "..."}

        Phase 3.5B: player_id is now always Blizzard ID.

        Args:
            player_id: Blizzard ID (canonical key)

        Returns:
            Dict with 'summary', 'profile', 'battletag', 'name' keys, or None if not found
        """
        profile = await self.storage.get_player_profile(player_id)
        if not profile:
            return None

        # Storage now returns full summary from summary_json column
        return {
            "profile": profile["html"],
            "summary": profile["summary"],  # Full summary with all fields
            "battletag": profile.get("battletag"),  # Optional metadata
            "name": profile.get("name"),  # Display name
        }

    async def update_player_profile_cache(
        self,
        player_id: str,
        player_summary: dict,
        html: str,
        battletag: str | None = None,
        name: str | None = None,
    ) -> None:
        """
        Update player profile in persistent storage.

        Phase 3.5B: Uses Blizzard ID as key, stores battletag/name as optional metadata.

        Args:
            player_id: Blizzard ID (canonical key)
            player_summary: Full summary from search endpoint (all fields), may be empty dict
            html: Raw career page HTML
            battletag: Full BattleTag from user input (e.g., "TeKrop-2217"), optional
            name: Display name from HTML or summary (e.g., "TeKrop"), optional
        """
        await self.storage.set_player_profile(
            player_id=player_id,
            html=html,
            summary=player_summary if player_summary else None,  # None if empty dict
            battletag=battletag,
            name=name,
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
                f"Player {player_id} (battletag : {player_status['battletag']}) is unknown "
                f"(retry in {retry_after_seconds}s, check #{player_status['check_count']})"
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
        self,
        blizzard_id: str,
        exception: HTTPException,
        battletag: str | None = None,
    ) -> None:
        """
        Mark player as unknown if 404 exception is raised.
        Implements exponential backoff for retries.

        Phase 3.5B: Store by Blizzard ID (primary) and BattleTag (if available).
        This enables early rejection of both Blizzard ID and BattleTag requests.

        Updates the exception detail to match PlayerNotFoundError format
        with retry_after, next_check_at, and check_count fields.

        Args:
            blizzard_id: Resolved Blizzard ID (always available after redirect)
            exception: HTTPException to modify and check for 404 status
            battletag: Optional BattleTag from user request (enables early check)
        """
        if not settings.unknown_players_cache_enabled:
            return

        if exception.status_code != status.HTTP_404_NOT_FOUND:
            return

        # Get existing status to increment check count
        player_status = await self.storage.get_player_status(blizzard_id)
        check_count = player_status["check_count"] + 1 if player_status else 1

        # Calculate exponential backoff and next check time
        retry_after = self._calculate_retry_after(check_count)
        next_check_at = int(time.time()) + retry_after

        # Store under Blizzard ID with optional BattleTag for early rejection
        await self.storage.set_player_status(
            blizzard_id, check_count, retry_after, battletag=battletag
        )

        # Update exception detail to match PlayerNotFoundError model
        exception.detail = {
            "error": "Player not found",
            "retry_after": retry_after,
            "next_check_at": next_check_at,
            "check_count": check_count,
        }

        logger.info(
            f"Marked player {blizzard_id} as unknown"
            f"{f' (battletag: {battletag})' if battletag else ''} "
            f"(check #{check_count}, retry in {retry_after}s, next check at {next_check_at})"
        )

    async def _resolve_player_identity(
        self, client: BlizzardClientPort, player_id: str
    ) -> tuple[str | None, dict, str | None, str | None]:
        """Resolve player identity via search and Blizzard ID redirect if needed.

        This method implements the identity resolution flow:
        1. Skip search if player_id is already a Blizzard ID
        2. Fetch and parse search results
        3. If not found, attempt Blizzard ID resolution via redirect (returns HTML)
        4. Re-parse search results with Blizzard ID if obtained

        Phase 3.5B: Returns Blizzard ID and BattleTag separately for proper key management.
        Note: Disambiguation (Step 3) removed as it requires BattleTag→Blizzard ID index.

        Args:
            client: Blizzard API client
            player_id: Player identifier (BattleTag or Blizzard ID)

        Returns:
            Tuple of (blizzard_id, player_summary, profile_html, battletag_input):
            - blizzard_id: Canonical Blizzard ID (cache key), None if not resolved yet
            - player_summary: dict from search (may be empty if direct Blizzard ID or not found)
            - profile_html: HTML from profile page if fetched during resolution, None otherwise
            - battletag_input: Original BattleTag from user input if applicable, None for Blizzard ID input
        """
        logger.info("Retrieving Player Summary...")

        # Skip search if player_id is already a Blizzard ID
        if is_blizzard_id(player_id):
            logger.info("Player ID is a Blizzard ID, skipping search")
            return player_id, {}, None, None  # Blizzard ID input, no BattleTag

        # User provided BattleTag - track it for storage
        battletag_input = player_id

        # Fetch and parse search results
        search_json = await fetch_player_summary_json(client, player_id)
        player_summary = parse_player_summary_json(search_json, player_id)

        if player_summary:
            logger.info("Player Summary retrieved!")
            blizzard_id = player_summary.get("url")
            return blizzard_id, player_summary, None, battletag_input

        # Player not found in search - try to resolve via Blizzard ID redirect
        logger.info("Player not found in search, attempting Blizzard ID resolution")
        # Step 1: Capture HTML from this call to avoid double-fetch
        html, blizzard_id = await fetch_player_html(client, player_id)

        if blizzard_id and search_json:
            logger.info(
                f"Got Blizzard ID from redirect: {blizzard_id}, re-parsing search results"
            )
            player_summary = parse_player_summary_json(
                search_json, player_id, blizzard_id
            )

            if player_summary:
                logger.info("Successfully resolved player via Blizzard ID")
                # Return the HTML we already fetched
                return blizzard_id, player_summary, html, battletag_input

            logger.warning(
                "Could not resolve player even with Blizzard ID from redirect"
            )

        # Always return HTML if we fetched it, even if blizzard_id or parsing failed
        # This avoids a second fetch in the controller
        return blizzard_id, {}, html, battletag_input
