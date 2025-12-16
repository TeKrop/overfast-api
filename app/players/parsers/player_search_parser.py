"""Player stats summary Parser module"""

from typing import TYPE_CHECKING

from app.config import settings
from app.overfast_logger import logger
from app.parsers import JSONParser

from ..helpers import get_player_title

if TYPE_CHECKING:
    from collections.abc import Iterable


class PlayerSearchParser(JSONParser):
    """Overwatch player search Parser class"""

    root_path = settings.search_account_path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_nickname = kwargs["name"]
        self.search_name = kwargs["name"].split("-", 1)[0]
        self.order_by = kwargs.get("order_by")
        self.offset = kwargs.get("offset")
        self.limit = kwargs.get("limit")

    def get_blizzard_url(self, **kwargs) -> str:
        """URL used when requesting data to Blizzard."""
        search_name = kwargs["name"].split("-", 1)[0]
        return f"{super().get_blizzard_url(**kwargs)}/{search_name}/"

    async def parse_data(self) -> dict:
        # First filter players given their name
        players = self.filter_players()

        # Transform into PlayerSearchResult format
        logger.info("Applying transformation..")
        players = self.apply_transformations(players)

        # Apply ordering
        logger.info("Applying ordering..")
        players = self.apply_ordering(players)

        players_list = {
            "total": len(players),
            "results": players[self.offset : self.offset + self.limit],
        }

        logger.info("Done ! Returning players list...")
        return players_list

    def filter_players(self) -> list[dict]:
        """Filter players before transforming. Ensure resulting players
        have the exact same name, with same letter case.
        """
        return [
            player
            for player in self.json_data
            if player["name"] == self.search_name and player["isPublic"] is True
        ]

    def apply_transformations(self, players: Iterable[dict]) -> list[dict]:
        """Apply transformations to found players in order to return the data
        in the OverFast API format. We'll also retrieve some data from parsers.
        """
        transformed_players = []

        for player in players:
            player_id = (
                self.search_nickname
                if len(players) == 1 and "-" in self.search_nickname
                else player["url"]
            )

            # Normalize optional fields that may be missing or inconsistently formatted
            # due to Blizzard's region-specific changes. In some regions, the "portrait"
            # field is still used instead of the newer "avatar", "namecard", or "title" fields.
            # If "portrait" is present, explicitly set "avatar", "namecard", and "title" to None
            # to ensure consistent data structure across all regions.
            if player.get("portrait"):
                player["avatar"] = None
                player["namecard"] = None
                player["title"] = None

            transformed_players.append(
                {
                    "player_id": player_id,
                    "name": player["name"],
                    "avatar": player["avatar"],
                    "namecard": player.get("namecard"),
                    "title": get_player_title(player.get("title")),
                    "career_url": f"{settings.app_base_url}/players/{player_id}",
                    "blizzard_id": player["url"],
                    "last_updated_at": player["lastUpdated"],
                    "is_public": player["isPublic"],
                },
            )
        return transformed_players

    def apply_ordering(self, players: list[dict]) -> list[dict]:
        """Apply the given ordering to the list of found players."""
        order_field, order_arrangement = self.order_by.split(":")
        players.sort(
            key=lambda player: player[order_field],
            reverse=order_arrangement == "desc",
        )
        return players
