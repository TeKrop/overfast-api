"""Namecard Parser module"""
from app.commands.update_namecards_cache import retrieve_namecards
from app.common.exceptions import ParserParsingError
from app.common.helpers import blizzard_response_error_from_request, overfast_request
from app.common.logging import logger
from app.config import settings

from .api_parser import APIParser


class NamecardParser(APIParser):
    """Namecard Parser class"""

    root_path = settings.search_account_path
    timeout = settings.career_path_cache_timeout
    cache_expiration_timeout = settings.career_parser_cache_expiration_timeout

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_id = kwargs.get("player_id")

    async def retrieve_and_parse_data(self) -> None:
        """Method used to retrieve data from Blizzard (JSON data), parsing it
        and storing it into self.data attribute.
        """
        req = await overfast_request(self.blizzard_url)
        if req.status_code not in self.valid_http_codes:
            raise blizzard_response_error_from_request(req)

        self.players = req.json()

        # Parse retrieved HTML data
        try:
            self.data = self.parse_data()
        except KeyError as error:
            raise ParserParsingError(repr(error)) from error

        # Update the Parser Cache
        self.cache_manager.update_parser_cache(self.cache_key, self.data, self.timeout)

    def parse_data(self) -> dict:
        # We'll use the battletag for searching
        player_battletag = self.player_id.replace("-", "#")

        # Find the right player
        try:
            player_data = next(
                player
                for player in self.players
                if player["battleTag"] == player_battletag
            )
        except StopIteration:
            # We didn't find the player, return nothing
            logger.warning(
                "Player {} not found in search results, couldn't retrieve its namecard",
                self.player_id,
            )
            return {"namecard": None}

        # If the player doesn't have any namecard, directly return nothing here
        if (
            "namecard" not in player_data
            or player_data["namecard"] == "0x0000000000000000"
        ):
            logger.info("Player {} doesn't have any namecard", self.player_id)
            return {"namecard": None}

        # Retrieve the possible matching value in the cache. If not in
        # cache (or Redis disabled), try to retrieve it directly.
        namecard_url = self.cache_manager.get_namecard_cache(player_data["namecard"])
        if not namecard_url:
            logger.warning(
                "URL for namecard {} of player {} not found in the cache",
                player_data["namecard"],
                self.player_id,
            )

            try:
                namecards = retrieve_namecards()
            except SystemExit:
                namecards = {}

            namecard_url = namecards.get(player_data["namecard"])

        # If we still didn't retrieve the URL, it means the player doesn't
        # have one, or we had an issue, log it and return None
        if not namecard_url:
            logger.warning(
                "URL for namecard {} of player {} not found at all",
                player_data["namecard"],
                self.player_id,
            )
            return {"namecard": None}

        return {"namecard": namecard_url}

    def get_blizzard_url(self, **kwargs) -> str:
        player_battletag = kwargs.get("player_id").replace("-", "#")
        return f"{super().get_blizzard_url(**kwargs)}/{player_battletag}"
