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
        self.player_name = self.player_id.split("-", 1)[0]

    async def parse_data(self) -> dict:
        # As the battletag is not available on search endpoint
        # anymore, we'll use the name for search, by taking case into account

        # Find the right player
        matching_players = [
            player
            for player in self.json_data
            if player["name"] == self.player_name and player["isPublic"] is True
        ]
        if len(matching_players) != 1:
            # We didn't find the player, return nothing
            logger.warning(
                "Player {} not found in search results ({} matching players)",
                self.player_id,
                len(matching_players),
            )
            return {}

        player_data = matching_players[0]

        # Normalize optional fields that may be missing or inconsistently formatted
        # due to Blizzard's region-specific changes. In some regions, the "portrait"
        # field is still used instead of the newer "avatar", "namecard", or "title" fields.
        # If "portrait" is present, explicitly set "avatar", "namecard", and "title" to None
        # to ensure consistent data structure across all regions.
        if player_data.get("portrait"):
            player_data["avatar"] = None
            player_data["namecard"] = None
            player_data["title"] = None

        return player_data

    def get_blizzard_url(self, **kwargs) -> str:
        player_name = kwargs.get("player_id").split("-", 1)[0]
        return f"{super().get_blizzard_url(**kwargs)}/{player_name}/"
