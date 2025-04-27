"""Player stats summary Parser module"""

from collections.abc import Iterable

from app.config import settings
from app.overfast_logger import logger
from app.parsers import JSONParser
from app.unlocks_manager import UnlocksManager

from ..helpers import get_player_title


class PlayerSearchParser(JSONParser):
    """Overwatch player search Parser class"""

    root_path = settings.search_account_path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_by = kwargs.get("order_by")
        self.offset = kwargs.get("offset")
        self.limit = kwargs.get("limit")
        self.unlocks_manager = UnlocksManager()

    def get_blizzard_url(self, **kwargs) -> str:
        """URL used when requesting data to Blizzard."""
        search_name = kwargs.get("name").split("-", 1)[0]
        return f"{super().get_blizzard_url(**kwargs)}/{search_name}/"

    async def parse_data(self) -> dict:
        # Transform into PlayerSearchResult format
        logger.info("Applying transformation..")
        players = await self.apply_transformations(self.json_data)

        # Apply ordering
        logger.info("Applying ordering..")
        players = self.apply_ordering(players)

        players_list = {
            "total": len(players),
            "results": players[self.offset : self.offset + self.limit],
        }

        logger.info("Done ! Returning players list...")
        return players_list

    async def apply_transformations(self, players: Iterable[dict]) -> list[dict]:
        """Apply transformations to found players in order to return the data
        in the OverFast API format. We'll also retrieve some data from parsers.
        """
        transformed_players = []

        # Retrieve and cache Unlock IDs
        unlock_ids = self.__retrieve_unlock_ids(players)
        await self.unlocks_manager.cache_values(unlock_ids)

        for player in players:
            player_id = player["battleTag"].replace("#", "-")

            transformed_players.append(
                {
                    "player_id": player_id,
                    "name": player["battleTag"],
                    "avatar": self.unlocks_manager.get(player["portrait"]),
                    "namecard": self.unlocks_manager.get(player["namecard"]),
                    "title": get_player_title(
                        self.unlocks_manager.get(player["title"])
                    ),
                    "career_url": f"{settings.app_base_url}/players/{player_id}",
                    "blizzard_id": player["url"],
                    "last_updated_at": player["lastUpdated"],
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

    def __retrieve_unlock_ids(self, players: list[dict]) -> set[str]:
        return {player[key] for player in players for key in settings.unlock_keys}
