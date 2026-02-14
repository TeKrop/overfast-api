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

    async def process_request(self, **kwargs) -> list[dict]:  # noqa: ARG002
        """Process request using stateless parser function"""
        data = parse_gamemodes()

        # Dual-write to API Cache (Valkey) and Storage (SQLite)
        storage_key = "gamemodes:en-us"  # Gamemodes are not localized
        await self.update_static_cache(data, storage_key, data_type="json")

        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
