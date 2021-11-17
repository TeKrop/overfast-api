"""Search Players Request Handler module"""
import json
from typing import Iterable

from fastapi import Request

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.helpers import blizzard_response_error, overfast_request
from overfastapi.common.logging import logger
from overfastapi.common.mixins import ApiRequestMixin
from overfastapi.config import (
    BLIZZARD_HOST,
    OVERFAST_API_BASE_URL,
    SEARCH_ACCOUNT_PATH,
    SEARCH_ACCOUNT_PATH_CACHE_TIMEOUT,
)


class SearchPlayersRequestHandler(ApiRequestMixin):
    """Search Players Request Handler used in order to find an Overwatch player
    using some filters : level, platform, career privacy, etc.

    The APIRequestHandler class is not used here, as this is a very specific request,
    depending on a Blizzard endpoint returning JSON Data, and without needing any parser.
    """

    timeout = SEARCH_ACCOUNT_PATH_CACHE_TIMEOUT
    cache_manager = CacheManager()

    def __init__(self, request: Request):
        self.cache_key = CacheManager.get_cache_key_from_request(request)

    def process_request(self, **kwargs) -> dict:
        """Main method used to process the request from user and return final data.

        The process uses API/Parser Cache if available and needed, the main steps are :
        - Make a request to Blizzard URL (if not using Cache API)
        - Instanciate the dedicated parser class with Blizzard response
        - Parse the page completely, apply filters, transformation and ordering
        - Update API Cache accordingly, and return the final result
        """

        # If we are using API Cache from inside the app
        # (no reverse proxy configured), check the API Cache
        if api_cache_data := self.get_api_cache_data():
            return api_cache_data

        # No API Cache or not using it in app, we request the data from Blizzard URL
        logger.info("No API Cache, requesting the data to Blizzard...")
        req = overfast_request(self.get_blizzard_url(**kwargs))
        if req.status_code != 200:
            raise blizzard_response_error(req)

        players = req.json()

        # Filter results using kwargs
        logger.info("Applying filters..")
        players = self.apply_filters(players, **kwargs)

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
        self.cache_manager.update_api_cache(
            self.cache_key, json.dumps(players_list), self.timeout
        )

        # Return filtered list
        logger.info("Done ! Returning players list...")
        return players_list

    @staticmethod
    def apply_filters(players: list[dict], **kwargs) -> Iterable[dict]:
        """Apply query params filters on a list of players (level, platform, career
        privacy), and return the results accordingly as an iterable.
        """
        filter_min_level = lambda p: not kwargs.get("min_level") or p[
            "level"
        ] >= kwargs.get("min_level")

        filter_max_level = lambda p: not kwargs.get("max_level") or p[
            "level"
        ] <= kwargs.get("max_level")

        filter_platform = lambda p: not kwargs.get("platform") or p[
            "platform"
        ] == kwargs.get("platform")

        filter_privacy = lambda p: not kwargs.get("privacy") or p["isPublic"] == (
            kwargs.get("privacy") == "public"
        )

        filters = (filter_min_level, filter_max_level, filter_platform, filter_privacy)
        return filter(lambda x: all(f(x) for f in filters), players)

    @staticmethod
    def apply_transformations(players: Iterable[dict]) -> list[dict]:
        """Apply transformations to found players in order to return the data
        in the OverFast API format.
        """
        return [
            {
                "player_id": player["urlName"],
                "name": player["name"],
                "level": player["level"],
                "platform": player["platform"],
                "privacy": "public" if player["isPublic"] else "private",
                "career_url": (
                    f"{OVERFAST_API_BASE_URL}"
                    "/players"
                    f"/{player['platform']}"
                    f"/{player['urlName']}"
                ),
            }
            for player in players
        ]

    @staticmethod
    def apply_ordering(players: list[dict], order_by: str) -> list[dict]:
        """Apply the given ordering to the list of found players."""
        order_field, order_arrangement = order_by.split(":")
        players.sort(
            key=lambda player: player[order_field], reverse=order_arrangement == "desc"
        )
        return players

    @staticmethod
    def get_blizzard_url(**kwargs) -> str:
        """URL used when requesting data to Blizzard."""
        return f"{BLIZZARD_HOST}/{SEARCH_ACCOUNT_PATH}/{kwargs.get('name')}"
