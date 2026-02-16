"""Base Player Controller module"""

import time
from functools import wraps
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.adapters.blizzard.parsers.player_profile import (
    extract_name_from_profile_html,
    fetch_player_html,
)
from app.adapters.blizzard.parsers.player_summary import (
    fetch_player_summary_json,
    parse_player_summary_json,
)
from app.adapters.blizzard.parsers.utils import is_blizzard_id
from app.config import settings
from app.controllers import AbstractController
from app.exceptions import ParserBlizzardError, ParserParsingError
from app.helpers import overfast_internal_error
from app.monitoring.metrics import (
    sqlite_battletag_lookup_total,
    sqlite_cache_hit_total,
    sqlite_unknown_player_rejections_total,
    storage_hits_total,
)
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
            # Track cache miss
            if settings.prometheus_enabled:
                sqlite_cache_hit_total.labels(
                    table="player_profiles", result="miss"
                ).inc()
                storage_hits_total.labels(result="miss").inc()
            return None

        # Track cache hit
        if settings.prometheus_enabled:
            sqlite_cache_hit_total.labels(table="player_profiles", result="hit").inc()
            storage_hits_total.labels(result="hit").inc()

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

            # Track early rejection
            if settings.prometheus_enabled:
                sqlite_unknown_player_rejections_total.inc()

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

    async def _enrich_summary_from_blizzard_id(
        self, client: BlizzardClientPort, blizzard_id: str
    ) -> tuple[dict, str | None]:
        """Reverse enrichment: fetch HTML, extract name, search for matching summary.

        When user provides a Blizzard ID directly, we can still enrich the response
        with player summary by extracting the name from HTML and searching.

        Args:
            client: Blizzard API client
            blizzard_id: Blizzard ID to enrich

        Returns:
            Tuple of (player_summary, html):
            - player_summary: Enriched summary dict if found, empty dict otherwise
            - html: Profile HTML (always returned if fetch succeeds)
        """
        # Fetch HTML to extract player name
        html, _ = await fetch_player_html(client, blizzard_id)

        if not html:
            logger.warning("Could not fetch HTML for Blizzard ID, no enrichment")
            return {}, None

        # Extract name from HTML (e.g., "TeKrop" from profile)
        try:
            player_name = extract_name_from_profile_html(html)

            if player_name:
                logger.info(
                    f"Extracted name '{player_name}', searching for matching summary"
                )
                # Search with the name to find summary
                search_json = await fetch_player_summary_json(client, player_name)
                # Find the entry that matches our Blizzard ID
                player_summary = parse_player_summary_json(
                    search_json, player_name, blizzard_id
                )

                if player_summary:
                    logger.info("Successfully enriched summary from name-based search")
                    return player_summary, html

                logger.warning(
                    f"Name '{player_name}' found in HTML but no matching summary in search"
                )
            else:
                logger.warning("Could not extract name from HTML for enrichment")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error during reverse enrichment: {e}")

        # Enrichment failed but we have HTML - return what we have
        return {}, html

    async def _resolve_player_identity(
        self, client: BlizzardClientPort, player_id: str
    ) -> tuple[str | None, dict, str | None, str | None]:
        """Resolve player identity via search and Blizzard ID redirect if needed.

        This method implements the identity resolution flow:
        1. If Blizzard ID: Attempt reverse enrichment (fetch HTML → extract name → search)
        2. If BattleTag: Fetch and parse search results
        3. If not found in search: Check SQLite for cached BattleTag→Blizzard ID mapping
        4. If still not found: Attempt Blizzard ID resolution via redirect (returns HTML)
        5. Re-parse search results with Blizzard ID if obtained

        Phase 3.5B optimizations:
        - SQLite lookup before redirect to avoid redundant Blizzard calls
        - Reverse enrichment: When Blizzard ID provided, extract name and search for summary
          This builds summary cache even when users provide direct Blizzard IDs

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

        # Blizzard ID provided - attempt reverse enrichment
        if is_blizzard_id(player_id):
            logger.info(
                "Player ID is a Blizzard ID, attempting reverse enrichment from name"
            )
            player_summary, html = await self._enrich_summary_from_blizzard_id(
                client, player_id
            )
            return player_id, player_summary, html, None

        # User provided BattleTag - track it for storage
        battletag_input = player_id

        # Fetch and parse search results
        search_json = await fetch_player_summary_json(client, player_id)
        player_summary = parse_player_summary_json(search_json, player_id)

        if player_summary:
            logger.info("Player Summary retrieved!")
            blizzard_id = player_summary.get("url")
            return blizzard_id, player_summary, None, battletag_input

        # Player not found in search - check SQLite cache before attempting redirect
        logger.info(
            "Player not found in search, checking SQLite for cached Blizzard ID mapping"
        )
        cached_blizzard_id = await self.storage.get_player_id_by_battletag(
            battletag_input
        )

        if cached_blizzard_id:
            # Track BattleTag lookup hit
            if settings.prometheus_enabled:
                sqlite_battletag_lookup_total.labels(result="hit").inc()

            logger.info(
                f"Found cached Blizzard ID {cached_blizzard_id} for {battletag_input}, "
                "skipping redirect"
            )
            # Re-parse search with cached Blizzard ID (handles multiple matches)
            player_summary = parse_player_summary_json(
                search_json, player_id, cached_blizzard_id
            )
            if player_summary:
                logger.info("Successfully resolved player using cached Blizzard ID")
                # No HTML since we skipped the redirect
                return cached_blizzard_id, player_summary, None, battletag_input

            logger.warning(
                "Cached Blizzard ID found but couldn't resolve player in search results"
            )
        # Track BattleTag lookup miss
        elif settings.prometheus_enabled:
            sqlite_battletag_lookup_total.labels(result="miss").inc()

        # Last resort: attempt Blizzard ID resolution via redirect
        logger.info("No cached mapping found, attempting Blizzard ID resolution")
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

    async def handle_player_request_exceptions(
        self,
        error: Exception,
        cache_key: str,
        battletag_input: str | None,
        player_summary: dict,
    ):
        """
        Shared exception handler for player controllers to eliminate code duplication.

        Handles ParserBlizzardError, ParserParsingError, and HTTPException uniformly
        across all player endpoints. Marks players as unknown on 404 errors.

        This method always raises - it processes the error and then re-raises it.

        Args:
            error: The exception that was caught
            cache_key: The cache key (usually Blizzard ID or player_id)
            battletag_input: BattleTag from user input (optional)
            player_summary: Player summary dict (may be empty)

        Raises:
            HTTPException: Always raises after processing the error
        """
        if isinstance(error, ParserBlizzardError):
            exception = HTTPException(
                status_code=error.status_code,
                detail=error.message,
            )
            # Mark unknown on 404 from Blizzard
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self.mark_player_unknown_on_404(
                    cache_key, exception, battletag=battletag_input
                )
            raise exception from error

        if isinstance(error, ParserParsingError):
            # Check if error message indicates player not found
            # This can happen when HTML structure is malformed or missing expected elements
            if "Could not find main content in HTML" in str(error):
                exception = HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Player not found",
                )
                # Mark unknown with Blizzard ID (primary) and BattleTag (if available)
                await self.mark_player_unknown_on_404(
                    cache_key, exception, battletag=battletag_input
                )
                raise exception from error

            # Get Blizzard URL for error reporting
            blizzard_url = (
                f"{settings.blizzard_host}{settings.career_path}/"
                f"{player_summary.get('url', cache_key) if player_summary else cache_key}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error

        if isinstance(error, HTTPException):
            # Mark unknown on any 404 (explicit HTTPException)
            if error.status_code == status.HTTP_404_NOT_FOUND:
                await self.mark_player_unknown_on_404(
                    cache_key, error, battletag=battletag_input
                )
            raise error

        # Unknown exception type - re-raise as-is
        raise error
