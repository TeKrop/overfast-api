"""Search Data Parser module"""

from app.config import settings
from app.overfast_logger import logger
from app.parsers import JSONParser


class SearchDataParser(JSONParser):
    """Static Data Parser class"""

    root_path = settings.search_account_path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_id = kwargs.get("player_id")

    async def parse_data(self) -> dict:
        # We'll use the battletag for searching
        player_battletag = self.player_id.replace("-", "#")

        # Find the right player
        try:
            player_data = next(
                player
                for player in self.json_data
                if (
                    player["battleTag"] == player_battletag
                    and player["isPublic"] is True
                )
            )
        except StopIteration:
            # We didn't find the player, return nothing
            logger.warning(
                "Player {} not found in search results, couldn't retrieve data",
                self.player_id,
            )
            return {}

        return player_data

    def get_blizzard_url(self, **kwargs) -> str:
        # Replace dash by encoded number sign (#) for search
        player_name = kwargs.get("player_id").split("-", 1)[0]
        return f"{super().get_blizzard_url(**kwargs)}/{player_name}/"
