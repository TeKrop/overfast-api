"""Base Player Controller module"""

from fastapi import HTTPException, status

from app.controllers import AbstractController


class BasePlayerController(AbstractController):
    """Base Player Controller used in order to ensure specific exceptions
    are properly handled. For instance, not found players should be cached
    to prevent spamming Blizzard with calls.
    """

    async def process_request(self, **kwargs) -> dict:
        """Process request as usual, but ensure to properly handle players
        we already know aren't existing to prevent spamming Blizzard.
        """

        # First check if player is known to not exist
        player_id = kwargs["player_id"]
        if self.cache_manager.is_player_unknown(player_id):
            self.cache_manager.increase_player_unknown_counter(player_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )

        # Then run process as usual, but intercept HTTP 404 to be able
        # to store result in cache, to prevent calling Blizzard next time
        try:
            return await super().process_request(**kwargs)
        except HTTPException as err:
            if err.status_code == status.HTTP_404_NOT_FOUND:
                self.cache_manager.increase_player_unknown_counter(player_id)
            raise
        else:
            # Player has been found and processed, reset counter
            self.cache_manager.reset_player_unknown_counter(player_id)
