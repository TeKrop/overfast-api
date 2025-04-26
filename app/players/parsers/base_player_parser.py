import httpx
from fastapi import status

from app.exceptions import ParserBlizzardError
from app.overfast_logger import logger
from app.parsers import HTMLParser
from app.players.parsers.search_data_parser import SearchDataParser


class BasePlayerParser(HTMLParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_id = kwargs.get("player_id")

        # Player Data is made of two sets of data :
        # - summary, retrieve from players search endpoint
        # - profile, gzipped HTML data from player profile page
        self.player_data = {"summary": None, "profile": None}

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{super().get_blizzard_url(**kwargs)}/{kwargs.get('player_id')}/"

    def store_response_data(self, response: httpx.Response) -> None:
        """Store HTML data in player_data to save for Player Cache"""
        super().store_response_data(response)
        self.player_data["profile"] = response.text

    async def parse(self) -> None:
        """Main parsing method for player profile routes"""

        # Check if we have up-to-date data in the Player Cache
        logger.info("Retrieving Player Summary...")
        self.player_data["summary"] = await self.__retrieve_player_summary_data()

        # If the player doesn't exist, summary will be empty, raise associated error
        if not self.player_data["summary"]:
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Player not found",
            )

        logger.info("Checking Player Cache...")
        player_cache = self.cache_manager.get_player_cache(self.player_id)
        if (
            player_cache is not None
            and player_cache["summary"]["lastUpdated"]
            == self.player_data["summary"]["lastUpdated"]
        ):
            logger.info("Player Cache found and up-to-date, using it")
            self.create_parser_tag(player_cache["profile"])
            self.parse_response_data()
            return

        # Data is not in Player Cache or not up-to-date,
        # we're retrieving data from Blizzard pages
        logger.info("Player Cache not found or not up-to-date, calling Blizzard")

        # Update URL with player summary URL
        self.blizzard_url = self.get_blizzard_url(
            player_id=self.player_data["summary"]["url"]
        )
        await super().parse()

        # Update the Player Cache
        self.cache_manager.update_player_cache(self.player_id, self.player_data)

    async def __retrieve_player_summary_data(self) -> dict | None:
        """Call Blizzard search page with user name to
        check last_updated_at and retrieve unlock values
        """
        player_summary_parser = SearchDataParser(player_id=self.player_id)
        await player_summary_parser.parse()
        return player_summary_parser.data
