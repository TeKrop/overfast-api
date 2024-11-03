"""Player stats summary Parser module"""

from collections.abc import Iterable

from app.config import settings
from app.overfast_logger import logger
from app.parsers import JSONParser

from ..helpers import get_player_title
from .search_data_parser import NamecardParser, PortraitParser, TitleParser


class PlayerSearchParser(JSONParser):
    """Overwatch player search Parser class"""

    root_path = settings.search_account_path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_by = kwargs.get("order_by")
        self.offset = kwargs.get("offset")
        self.limit = kwargs.get("limit")

    def get_blizzard_url(self, **kwargs) -> str:
        """URL used when requesting data to Blizzard."""
        return f"{super().get_blizzard_url(**kwargs)}/{kwargs.get('name')}/"

    def parse_data(self) -> dict:
        # Transform into PlayerSearchResult format
        logger.info("Applying transformation..")
        players = self.apply_transformations(self.json_data)

        # Apply ordering
        logger.info("Applying ordering..")
        players = self.apply_ordering(players)

        players_list = {
            "total": len(players),
            "results": players[self.offset : self.offset + self.limit],
        }

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
                    "avatar": self.__get_avatar_url(player, player_id),
                    "namecard": self.__get_namecard_url(player, player_id),
                    "title": self.__get_title(player, player_id),
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

    def __get_avatar_url(self, player: dict, player_id: str) -> str | None:
        return PortraitParser(player_id=player_id).retrieve_data_value(player)

    def __get_namecard_url(self, player: dict, player_id: str) -> str | None:
        return NamecardParser(player_id=player_id).retrieve_data_value(player)

    def __get_title(self, player: dict, player_id: str) -> str | None:
        title = TitleParser(player_id=player_id).retrieve_data_value(player)
        return get_player_title(title)
