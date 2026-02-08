"""Search Players Controller module"""

from typing import ClassVar

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_search import parse_player_search
from app.config import settings
from app.controllers import AbstractController


class SearchPlayersController(AbstractController):
    """Search Players Controller used in order to find an Overwatch player"""

    parser_classes: ClassVar[list] = []
    timeout = settings.search_account_path_cache_timeout

    async def process_request(self, **kwargs) -> dict:
        """Process request using stateless parser function"""
        client = BlizzardClient()

        data = await parse_player_search(
            client,
            name=kwargs["name"],
            order_by=kwargs.get("order_by", "name:asc"),
            offset=kwargs.get("offset", 0),
            limit=kwargs.get("limit", 10),
        )

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
