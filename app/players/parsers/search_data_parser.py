"""Search Data Parser module"""

from abc import ABC, abstractmethod

from app.config import settings
from app.overfast_logger import logger
from app.parsers import JSONParser

from ..enums import SearchDataType


class SearchDataParser(JSONParser, ABC):
    """Static Data Parser class"""

    root_path = settings.search_account_path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_id = kwargs.get("player_id")

    @property
    @abstractmethod
    def data_type(self) -> SearchDataType:
        """Data for which the Parser is implemented (namecard, title, etc.)"""

    def parse_data(self) -> dict:
        # We'll use the battletag for searching
        player_battletag = self.player_id.replace("-", "#")

        # Find the right player
        try:
            player_data = next(
                player
                for player in self.json_data
                if player["battleTag"] == player_battletag
            )
        except StopIteration:
            # We didn't find the player, return nothing
            logger.warning(
                "Player {} not found in search results, couldn't retrieve its {}",
                self.player_id,
                self.data_type,
            )
            return {self.data_type: None}

        # Once we found the player, retrieve the data url
        data_value = self.retrieve_data_value(player_data)
        return {self.data_type: data_value}

    def get_blizzard_url(self, **kwargs) -> str:
        player_battletag = kwargs.get("player_id").replace("-", "#")
        return f"{super().get_blizzard_url(**kwargs)}/{player_battletag}"

    def retrieve_data_value(self, player_data: dict) -> str | None:
        # If the player doesn't have any related data, directly return nothing here
        if (
            self.data_type not in player_data
            or player_data[self.data_type] == "0x0000000000000000"
        ):
            logger.info("Player {} doesn't have any {}", self.player_id, self.data_type)
            return None

        # Retrieve the possible matching value in the cache
        data_value = self.cache_manager.get_search_data_cache(
            self.data_type, player_data[self.data_type]
        )

        # If we didn't retrieve the URL, it means the player doesn't
        # have one, or we had an issue, log it and return None
        if not data_value:
            logger.warning(
                "URL for {} {} of player {} not found at all",
                self.data_type,
                player_data[self.data_type],
                self.player_id,
            )
            return None

        return data_value


class NamecardParser(SearchDataParser):
    """Namecard Parser class"""

    data_type = SearchDataType.NAMECARD


class PortraitParser(SearchDataParser):
    """Portrait Parser class"""

    data_type = SearchDataType.PORTRAIT


class TitleParser(SearchDataParser):
    """Title Parser class"""

    data_type = SearchDataType.TITLE


class LastUpdatedAtParser(SearchDataParser):
    """LastUpdatedAt Parser class"""

    data_type = SearchDataType.LAST_UPDATED_AT

    def retrieve_data_value(self, player_data: dict) -> int:
        return player_data["lastUpdated"]


class PlayerSummaryParser(SearchDataParser):
    """Player Summary Parser"""

    data_type = SearchDataType.SUMMARY

    def retrieve_data_value(self, player_data: dict) -> dict:
        return player_data
