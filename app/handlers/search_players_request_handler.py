"""Search Players Request Handler module"""

from collections.abc import Iterable

from fastapi import Request, status

from app.common.cache_manager import CacheManager
from app.common.enums import Locale
from app.common.helpers import (
    blizzard_response_error_from_request,
    get_player_title,
    overfast_request,
)
from app.common.logging import logger
from app.config import settings
from app.parsers.search_data_parser import NamecardParser, PortraitParser, TitleParser


class SearchPlayersRequestHandler:
    """Search Players Request Handler used in order to find an Overwatch player

    The APIRequestHandler class is not used here, as this is a very specific request,
    depending on a Blizzard endpoint returning JSON Data. Some parsers are used,
    but only to compute already downloaded data, we don't want them to retrieve
    Blizzard data as when we call their general parse() method.
    """

    timeout = settings.search_account_path_cache_timeout
    cache_manager = CacheManager()

    def __init__(self, request: Request):
        self.cache_key = CacheManager.get_cache_key_from_request(request)

    async def process_request(self, **kwargs) -> dict:
        """Main method used to process the request from user and return final data.

        The main steps are :
        - Make a request to Blizzard URL
        - Instanciate the dedicated parser class with Blizzard response
        - Parse the page completely, apply filters, transformation and ordering
        - Update API Cache accordingly, and return the final result
        """

        # Request the data from Blizzard URL
        req = await overfast_request(self.get_blizzard_url(**kwargs))
        if req.status_code != status.HTTP_200_OK:
            raise blizzard_response_error_from_request(req)

        players = req.json()

        # Transform into PlayerSearchResult format
        logger.info("Applying transformation..")
        players = self.apply_transformations(players)

        # Apply ordering
        logger.info("Applying ordering..")
        players = self.apply_ordering(players, kwargs.get("order_by"))

        offset = kwargs.get("offset")
        limit = kwargs.get("limit")

        players_list = {
            "total": len(players),
            "results": players[offset : offset + limit],
        }

        # Update API Cache
        logger.info("Updating API Cache...")
        self.cache_manager.update_api_cache(self.cache_key, players_list, self.timeout)

        # Return filtered list
        logger.info("Done ! Returning players list...")
        return players_list

    def apply_transformations(self, players: Iterable[dict]) -> list[dict]:
        """Apply transformations to found players in order to return the data
        in the OverFast API format. We'll also retrieve some data from parsers.
        """
        transformed_players = []
        for player in players:
            player_id = player["battleTag"].replace("#", "-")
            transformed_players.append(
                {
                    "player_id": player_id,
                    "name": player["battleTag"],
                    "avatar": self.get_avatar_url(player, player_id),
                    "namecard": self.get_namecard_url(player, player_id),
                    "title": self.get_title(player, player_id),
                    "career_url": f"{settings.app_base_url}/players/{player_id}",
                    "blizzard_id": player["url"],
                },
            )
        return transformed_players

    @staticmethod
    def apply_ordering(players: list[dict], order_by: str) -> list[dict]:
        """Apply the given ordering to the list of found players."""
        order_field, order_arrangement = order_by.split(":")
        players.sort(
            key=lambda player: player[order_field],
            reverse=order_arrangement == "desc",
        )
        return players

    @staticmethod
    def get_blizzard_url(**kwargs) -> str:
        """URL used when requesting data to Blizzard."""
        locale = Locale.ENGLISH_US
        return f"{settings.blizzard_host}/{locale}{settings.search_account_path}/{kwargs.get('name')}/"

    def get_avatar_url(self, player: dict, player_id: str) -> str | None:
        return PortraitParser(player_id=player_id).retrieve_data_value(player)

    def get_namecard_url(self, player: dict, player_id: str) -> str | None:
        return NamecardParser(player_id=player_id).retrieve_data_value(player)

    def get_title(self, player: dict, player_id: str) -> str | None:
        title = TitleParser(player_id=player_id).retrieve_data_value(player)
        return get_player_title(title)
