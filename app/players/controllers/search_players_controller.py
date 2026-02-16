"""Search Players Controller module"""

from typing import ClassVar

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.player_search import parse_player_search
from app.config import settings
from app.controllers import AbstractController
from app.exceptions import ParserParsingError
from app.helpers import overfast_internal_error


class SearchPlayersController(AbstractController):
    """Search Players Controller used in order to find an Overwatch player"""

    parser_classes: ClassVar[list] = []
    timeout = settings.search_account_path_cache_timeout

    async def process_request(self, **kwargs) -> dict:
        """Process request using stateless parser function"""
        client = BlizzardClient()

        try:
            data = await parse_player_search(
                client,
                name=kwargs["name"],
                order_by=kwargs.get("order_by", "name:asc"),
                offset=kwargs.get("offset", 0),
                limit=kwargs.get("limit", 10),
            )
        except ParserParsingError as error:
            # Get Blizzard URL for error reporting
            search_name = kwargs["name"].split("-", 1)[0]
            blizzard_url = (
                f"{settings.blizzard_host}{settings.search_account_path}/{search_name}/"
            )
            raise overfast_internal_error(blizzard_url, error) from error

        # Update API Cache
        await self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
