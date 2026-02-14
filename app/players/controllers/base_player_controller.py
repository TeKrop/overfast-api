"""Base Player Controller module"""

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

    async def check_unknown_player(self, player_id: str) -> None:
        """
        Check if player is known to not exist and raise 404 if so.
        Should be called at the start of any player controller logic.

        Args:
            player_id: Player ID to check

        Raises:
            HTTPException: 404 if player is known to not exist
        """
        if not settings.unknown_players_cache_enabled:
            return

        if await self.cache_manager.is_player_unknown(player_id):
            logger.warning(
                "Player {} is unknown, skipping profile retrieval", player_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )

    async def mark_player_unknown_on_404(
        self, player_id: str, exception: HTTPException
    ) -> None:
        """
        Mark player as unknown if 404 exception is raised.
        Should be called in exception handler of player controllers.

        Args:
            player_id: Player ID to mark
            exception: HTTPException to check for 404 status
        """
        if not settings.unknown_players_cache_enabled:
            return

        if exception.status_code == status.HTTP_404_NOT_FOUND:
            await self.cache_manager.set_player_as_unknown(player_id)

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
        """

        # Ensure unknown players caching system is enabled
        if not settings.unknown_players_cache_enabled:
            return cast("dict", await super().process_request(**kwargs))

        # First check if player is known to not exist
        player_id = kwargs["player_id"]
        if await self.cache_manager.is_player_unknown(player_id):
            logger.warning(
                "Player {} is unknown, skipping profile retrieval", player_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )

        # Then run process as usual, but intercept HTTP 404 to be able
        # to store result in cache, to prevent calling Blizzard next time
        try:
            return cast("dict", await super().process_request(**kwargs))
        except HTTPException as err:
            if err.status_code == status.HTTP_404_NOT_FOUND:
                await self.cache_manager.set_player_as_unknown(player_id)
            raise
