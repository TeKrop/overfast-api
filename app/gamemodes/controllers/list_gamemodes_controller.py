"""List Gamemodes Controller module"""

from typing import ClassVar

from app.adapters.blizzard.parsers.gamemodes import parse_gamemodes
from app.config import settings
from app.controllers import AbstractController


class ListGamemodesController(AbstractController):
    """List Gamemodes Controller used in order to retrieve a list of
    available Overwatch gamemodes.
    """

    parser_classes: ClassVar[list[type]] = []
    timeout = settings.csv_cache_timeout

    async def process_request(self, **kwargs) -> list[dict]:
        """Process request using stateless parser function"""
        data = parse_gamemodes()

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
